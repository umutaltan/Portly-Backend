from fastapi import APIRouter
from app.services import market_data_service

router = APIRouter()

@router.get("/price/{symbol}")
def get_price(symbol: str):
    return market_data_service.get_stock_data(symbol)
from typing import Optional

@router.get("/history/{symbol}")
def get_price_history(symbol: str, period: str = "1mo"):
    """
    Bir hissenin geçmiş fiyat verilerini döndürür.
    period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max
    """
    return market_data_service.get_stock_history(symbol=symbol, period=period)