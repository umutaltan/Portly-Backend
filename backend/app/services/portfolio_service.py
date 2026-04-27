from sqlalchemy.orm import Session
from app.models.portfolio import Portfolio
from app.services.market_data_service import get_stock_data
import yfinance as yf


def get_user_portfolio(db: Session, user_id: int):
    portfolio_items = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()
    result = []

    for item in portfolio_items:
        quantity = float(item.quantity)
        avg_cost = float(item.average_cost) 
        
        try:
            ticker = yf.Ticker(item.symbol)
            current_price = ticker.info.get('currentPrice') or ticker.info.get('regularMarketPrice') or ticker.info.get('previousClose')
            if current_price is None:
                current_price = avg_cost
        except Exception:
            current_price = avg_cost

        current_price = float(current_price)

        total_value = quantity * current_price
        total_cost = quantity * avg_cost
        pnl = total_value - total_cost
        pnl_percent = (pnl / total_cost * 100) if total_cost > 0 else 0.0

        result.append({
            "symbol": item.symbol,
            "quantity": quantity,
            "average_cost": avg_cost,
            "current_price": current_price,
            "total_value": total_value,
            "pnl": pnl,
            "pnl_percent": pnl_percent
        })

    return result

_SECTOR_TRANSLATIONS = {
    "Technology": "Teknoloji",
    "Financial Services": "Finans",
    "Financial": "Finans",
    "Consumer Cyclical": "Tüketim",
    "Consumer Defensive": "Temel Tüketim",
    "Communication Services": "İletişim",
    "Healthcare": "Sağlık",
    "Industrials": "Sanayi",
    "Energy": "Enerji",
    "Basic Materials": "Hammadde",
    "Real Estate": "Gayrimenkul",
    "Utilities": "Kamu Hizmetleri",
}


_sector_cache = {}


_FALLBACK_SECTORS = {
    "GC=F": "Altın",
    "SI=F": "Gümüş",
    "CL=F": "Petrol",
    "USDTRY=X": "Döviz",
    "EURTRY=X": "Döviz",
    "GBPTRY=X": "Döviz",
    "BTC-USD": "Kripto",
    "ETH-USD": "Kripto",
    "SOL-USD": "Kripto",
}


def _resolve_sector(symbol: str) -> str:
    """yfinance'tan sektör bilgisi çek, yoksa fallback'e bak, yoksa 'Diğer'."""
    symbol = symbol.upper()

    if symbol in _sector_cache:
        return _sector_cache[symbol]

    if symbol in _FALLBACK_SECTORS:
        sector = _FALLBACK_SECTORS[symbol]
        _sector_cache[symbol] = sector
        return sector

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        en_sector = info.get("sector") or info.get("industry")
        if en_sector:
            tr_sector = _SECTOR_TRANSLATIONS.get(en_sector, en_sector)
            _sector_cache[symbol] = tr_sector
            return tr_sector
    except Exception:
        pass

    _sector_cache[symbol] = "Diğer"
    return "Diğer"


def get_sector_breakdown(db: Session, user_id: int):
    """Kullanıcı portföyünü sektörlere göre dağıtır - nakit dahil."""
    portfolio = get_user_portfolio(db, user_id)

    from app.models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    cash_balance = float(user.balance) if user else 0.0

    if not portfolio and cash_balance == 0:
        return {"sectors": [], "total_value": 0.0}

    sector_totals = {}

    if portfolio:
        from concurrent.futures import ThreadPoolExecutor
        symbols = [item["symbol"] for item in portfolio]
        with ThreadPoolExecutor(max_workers=8) as ex:
            sector_list = list(ex.map(_resolve_sector, symbols))

        for item, sector in zip(portfolio, sector_list):
            value = item["total_value"]
            sector_totals[sector] = sector_totals.get(sector, 0.0) + value

    if cash_balance > 0:
        sector_totals["Nakit"] = cash_balance

    total = sum(sector_totals.values())
    sectors = [
        {
            "name": name,
            "value": round(value, 2),
            "percent": round((value / total * 100) if total > 0 else 0, 2),
        }
        for name, value in sorted(
            sector_totals.items(), key=lambda x: x[1], reverse=True
        )
    ]

    return {"sectors": sectors, "total_value": round(total, 2)}