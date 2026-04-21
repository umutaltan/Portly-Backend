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