from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.trade_schema import TradeRequest, TradeResponse
from app.services import order_service

router = APIRouter()

@router.post("/order", response_model=TradeResponse)
def place_order(trade_req: TradeRequest, db: Session = Depends(get_db)):
    return order_service.execute_trade(db=db, trade_req=trade_req)