from fastapi import APIRouter
from app.services import market_data_service

router = APIRouter()

@router.get("/price/{symbol}")
def get_price(symbol: str):
    return market_data_service.get_stock_data(symbol)