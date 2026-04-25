import math
import random
import statistics
from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.services import market_data_service, portfolio_service


# Tarihsel kriz parametreleri (gerçek piyasa verilerinden)
CRISIS_SCENARIOS = {
    "subprime_2008": {
        "name": "2008 Subprime Krizi",
        "description": "Lehman Brothers iflası, Eylül 2008. S&P 500 6 ayda %38 düştü.",
        "daily_drift": -0.0024,      # Günlük ortalama getiri (negatif)
        "daily_volatility": 0.041,    # VIX 80'lere fırladı
        "duration_days": 30,
        "academic": "Reinhart & Rogoff (2009) - This Time Is Different",
    },
    "covid_2020": {
        "name": "2020 COVID Çöküşü",
        "description": "Mart 2020 küresel pandemi. Piyasalar 30 günde %34 düştü.",
        "daily_drift": -0.0048,
        "daily_volatility": 0.058,
        "duration_days": 30,
        "academic": "Baker et al. (2020) - COVID-Induced Economic Uncertainty",
    },
    "bist_2018": {
        "name": "2018 BIST/TL Krizi",
        "description": "Ağustos 2018, TL %40 değer kaybetti, BIST %20 düştü.",
        "daily_drift": -0.0033,
        "daily_volatility": 0.038,
        "duration_days": 30,
        "academic": "Akıncı & Olmstead-Rumsey (2018) - EM Capital Flow Volatility",
    },
    "black_swan": {
        "name": "Siyah Kuğu (Rastgele)",
        "description": "Taleb'in 'The Black Swan' konsepti: öngörülemeyen ekstrem olay.",
        "daily_drift": -0.005,
        "daily_volatility": 0.07,
        "duration_days": 30,
        "academic": "Taleb (2007) - The Black Swan",
    },
}


def _get_portfolio_value(db: Session, user_id: int) -> tuple:
    """Mevcut portföy değerini ve ağırlıklarını hesapla."""
    holdings = portfolio_service.get_user_portfolio(db, user_id)
    if not holdings:
        return 0.0, []

    total = sum(h["total_value"] for h in holdings)
    weighted = []
    for h in holdings:
        weight = h["total_value"] / total if total > 0 else 0
        weighted.append({
            "symbol": h["symbol"],
            "weight": round(weight, 4),
            "value": h["total_value"],
        })
    return total, weighted


def _gbm_simulation(
    initial_value: float,
    daily_drift: float,
    daily_vol: float,
    days: int,
    n_simulations: int = 10000,
) -> dict:
    """
    Geometric Brownian Motion - Markowitz/Black-Scholes klasik finansal model.
    dS = μ*S*dt + σ*S*dW
    """
    # Tüm path'leri sakla (fan chart için gerekli)
    all_paths = []
    final_values = []

    for sim in range(n_simulations):
        value = initial_value
        path = [value]
        for _ in range(days):
            z = random.gauss(0, 1)
            value *= math.exp((daily_drift - 0.5 * daily_vol ** 2) + daily_vol * z)
            path.append(value)
        all_paths.append(path)
        final_values.append(value)

    final_values.sort()

    # === FAN CHART İÇİN PERCENTILE BANTLARI ===
    fan_chart_data = []
    for day in range(days + 1):
        day_values = sorted([path[day] for path in all_paths])
        fan_chart_data.append({
            "day": day,
            "p5": round(day_values[int(n_simulations * 0.05)], 2),
            "p25": round(day_values[int(n_simulations * 0.25)], 2),
            "p50": round(day_values[int(n_simulations * 0.50)], 2),
            "p75": round(day_values[int(n_simulations * 0.75)], 2),
            "p95": round(day_values[int(n_simulations * 0.95)], 2),
        })

    # İstatistikler
    mean = statistics.mean(final_values)
    median = statistics.median(final_values)
    p5 = final_values[int(n_simulations * 0.05)]
    p95 = final_values[int(n_simulations * 0.95)]
    var_95 = initial_value - p5
    cvar_95 = initial_value - statistics.mean(final_values[:int(n_simulations * 0.05)])

    # Olasılık dağılımı (histogram için 20 bucket)
    min_val = min(final_values)
    max_val = max(final_values)
    bucket_size = (max_val - min_val) / 20 if max_val > min_val else 1
    histogram = [0] * 20
    for v in final_values:
        idx = min(int((v - min_val) / bucket_size), 19)
        histogram[idx] += 1

    histogram_data = [
        {
            "value": round(min_val + i * bucket_size, 2),
            "count": histogram[i],
        }
        for i in range(20)
    ]

    return {
        "initial_value": round(initial_value, 2),
        "mean": round(mean, 2),
        "median": round(median, 2),
        "p5_worst_case": round(p5, 2),
        "p95_best_case": round(p95, 2),
        "var_95": round(var_95, 2),
        "cvar_95": round(cvar_95, 2),
        "expected_return_pct": round((mean - initial_value) / initial_value * 100, 2),
        "worst_case_pct": round((p5 - initial_value) / initial_value * 100, 2),
        "best_case_pct": round((p95 - initial_value) / initial_value * 100, 2),
        "n_simulations": n_simulations,
        "days": days,
        "histogram": histogram_data,
        "fan_chart": fan_chart_data,  # ← YENİ
    }


def run_monte_carlo(db: Session, user_id: int, scenario: str = "normal") -> dict:
    """Ana fonksiyon: Monte Carlo simülasyonu."""
    portfolio_value, weights = _get_portfolio_value(db, user_id)

    if portfolio_value == 0:
        return {
            "has_portfolio": False,
            "message": "Stres testi için en az bir hisse pozisyonu gerekli.",
        }

    if scenario == "normal":
        # Normal piyasa: tarihsel S&P 500 ortalamaları
        scenario_data = {
            "name": "Normal Piyasa Koşulları",
            "description": "Tarihsel S&P 500 ortalamaları kullanılır.",
            "daily_drift": 0.0004,
            "daily_volatility": 0.012,
            "duration_days": 30,
            "academic": "Markowitz (1952) - Modern Portfolio Theory",
        }
    else:
        if scenario not in CRISIS_SCENARIOS:
            scenario = "subprime_2008"
        scenario_data = CRISIS_SCENARIOS[scenario]

    sim_result = _gbm_simulation(
        initial_value=portfolio_value,
        daily_drift=scenario_data["daily_drift"],
        daily_vol=scenario_data["daily_volatility"],
        days=scenario_data["duration_days"],
    )

    return {
        "has_portfolio": True,
        "scenario_id": scenario,
        "scenario_name": scenario_data["name"],
        "scenario_description": scenario_data["description"],
        "academic_reference": scenario_data["academic"],
        "portfolio_weights": weights,
        "simulation": sim_result,
    }


def list_scenarios() -> list:
    """Mevcut senaryoların listesi."""
    scenarios = [
        {
            "id": "normal",
            "name": "Normal Piyasa",
            "description": "Tarihsel ortalama volatilite",
            "icon": "trending_flat",
        }
    ]
    for sid, sdata in CRISIS_SCENARIOS.items():
        scenarios.append({
            "id": sid,
            "name": sdata["name"],
            "description": sdata["description"],
            "icon": "warning",
        })
    return scenarios