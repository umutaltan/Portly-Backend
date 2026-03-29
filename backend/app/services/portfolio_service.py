from sqlalchemy.orm import Session
from app.models.portfolio import Portfolio
from app.services.market_data_service import get_stock_data

def get_user_portfolio(db: Session, user_id: int):
    portfolio_items = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()
    result = []
    
    for item in portfolio_items:
        market_data = get_stock_data(item.symbol)
        current_price = market_data["current_price"]
        
        cost_basis = item.average_cost * item.quantity
        total_value = current_price * item.quantity
        pnl = total_value - cost_basis
        pnl_percent = (pnl / cost_basis) * 100 if cost_basis > 0 else 0.0

        result.append({
            "symbol": item.symbol,
            "quantity": item.quantity,
            "average_cost": round(item.average_cost, 2),
            "current_price": current_price,
            "total_value": round(total_value, 2),
            "pnl": round(pnl, 2),
            "pnl_percent": round(pnl_percent, 2)
        })
        
    return result