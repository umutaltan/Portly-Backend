import yfinance as yf
from fastapi import HTTPException
from datetime import datetime, timedelta

_cache = {}
_CACHE_TTL_SECONDS = 60

def get_stock_data(symbol: str):
    symbol = symbol.upper()
    now = datetime.now()
    if symbol in _cache:
        data, ts = _cache[symbol]
        if now - ts < timedelta(seconds=_CACHE_TTL_SECONDS):
            return data
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d")
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"Sembol bulunamadı: {symbol}")
        current_price = float(hist['Close'].iloc[-1])
        if len(hist) >= 2:
            prev_close = float(hist['Close'].iloc[-2])
            change_percent = ((current_price - prev_close) / prev_close) * 100
        else:
            change_percent = 0.0
        try:
            info = ticker.info
            company_name = info.get("longName") or info.get("shortName") or symbol
        except Exception:
            company_name = symbol
        result = {
            "symbol": symbol,
            "company_name": company_name,
            "current_price": round(current_price, 2),
            "change_percent": round(change_percent, 2),
        }
        _cache[symbol] = (result, now)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Veri alınamadı: {str(e)}")
    # Geçmiş veri için ayrı cache (daha uzun TTL, çünkü değişmez)
_history_cache = {}
_HISTORY_CACHE_TTL_SECONDS = 300  # 5 dakika


def get_stock_history(symbol: str, period: str = "1mo"):
    """
    Hisse senedinin geçmiş fiyat verilerini döndürür.
    Flutter tarafında fl_chart için uygun format: [{date, close}].
    """
    symbol = symbol.upper()
    cache_key = f"{symbol}:{period}"
    now = datetime.now()

    # Cache kontrolü
    if cache_key in _history_cache:
        data, ts = _history_cache[cache_key]
        if now - ts < timedelta(seconds=_HISTORY_CACHE_TTL_SECONDS):
            return data

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)

        if hist.empty:
            raise HTTPException(status_code=404, detail=f"Geçmiş veri bulunamadı: {symbol}")

        # DataFrame'i Flutter'ın kolay işleyeceği formata dönüştür
        history = []
        for date, row in hist.iterrows():
            history.append({
                "date": date.strftime("%Y-%m-%d"),
                "timestamp": int(date.timestamp()),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })

        result = {
            "symbol": symbol,
            "period": period,
            "data": history,
            "data_points": len(history),
        }

        _history_cache[cache_key] = (result, now)
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Geçmiş veri alınamadı: {str(e)}")