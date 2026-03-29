from pydantic import BaseModel
from datetime import datetime

class TradeRequest(BaseModel):
    user_id: int
    symbol: str
    quantity: float
    transaction_type: str

class TradeResponse(BaseModel):
    id: int
    symbol: str
    transaction_type: str
    quantity: float
    price: float
    timestamp: datetime

    class Config:
        from_attributes = True