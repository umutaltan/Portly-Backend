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
    # Arama için cache
_search_cache = {}
_SEARCH_CACHE_TTL_MINUTES = 30


def search_symbols(query: str, limit: int = 10):
    """
    yfinance Search API'sini kullanarak hisse/şirket arar.
    BIST, NYSE, NASDAQ, kripto - hepsi tek endpoint'ten.
    """
    query = query.strip()
    if len(query) < 1:
        return []

    cache_key = query.lower()
    now = datetime.now()

    # Cache kontrolü (rate limit'e takılmamak için)
    if cache_key in _search_cache:
        data, ts = _search_cache[cache_key]
        if now - ts < timedelta(minutes=_SEARCH_CACHE_TTL_MINUTES):
            return data[:limit]

    try:
        # yfinance Search - en yeni API (yfinance >= 0.2.50)
        search = yf.Search(query, max_results=limit, news_count=0)
        quotes = search.quotes  # Liste of dicts

        results = []
        for q in quotes:
            symbol = q.get("symbol", "")
            if not symbol:
                continue

            # Market sınıflandırması
            exchange = q.get("exchange", "").upper()
            quote_type = q.get("quoteType", "").upper()

            if symbol.endswith(".IS"):
                market = "BIST"
            elif quote_type == "CRYPTOCURRENCY":
                market = "CRYPTO"
            elif exchange in ("NMS", "NASDAQ"):
                market = "NASDAQ"
            elif exchange in ("NYQ", "NYSE"):
                market = "NYSE"
            elif quote_type == "ETF":
                market = "ETF"
            elif quote_type == "INDEX":
                market = "ENDEKS"
            else:
                market = exchange or "DİĞER"

            results.append({
                "symbol": symbol,
                "name": q.get("shortname") or q.get("longname") or symbol,
                "market": market,
                "type": quote_type,
            })

        # Cache'e kaydet
        _search_cache[cache_key] = (results, now)
        return results[:limit]

    except Exception as e:
        # API hatası durumunda boş liste dön (frontend fallback'a düşer)
        print(f"Search error for '{query}': {e}")
        return []