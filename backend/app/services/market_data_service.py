import yfinance as yf
from fastapi import HTTPException

def get_stock_data(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")
        if data.empty:
            raise HTTPException(status_code=404, detail="Sembol bulunamadı")
        
        current_price = data['Close'].iloc[-1]
        return {
            "symbol": symbol.upper(),
            "current_price": round(current_price, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))