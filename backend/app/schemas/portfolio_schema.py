from pydantic import BaseModel

class PortfolioItemResponse(BaseModel):
    symbol: str
    quantity: float
    average_cost: float
    current_price: float
    total_value: float
    pnl: float
    pnl_percent: float