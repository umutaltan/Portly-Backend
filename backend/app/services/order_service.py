from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.schemas.trade_schema import TradeRequest
from app.services.market_data_service import get_stock_data

def execute_trade(db: Session, trade_req: TradeRequest):
    user = db.query(User).filter(User.id == trade_req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    market_data = get_stock_data(trade_req.symbol)
    current_price = market_data["current_price"]
    total_cost = current_price * trade_req.quantity

    if trade_req.transaction_type == "BUY":
        if user.balance < total_cost:
            raise HTTPException(status_code=400, detail="Yetersiz bakiye")
        
        user.balance -= total_cost
        
        portfolio_item = db.query(Portfolio).filter(
            Portfolio.user_id == user.id, 
            Portfolio.symbol == trade_req.symbol.upper()
        ).first()

        if portfolio_item:
            total_value = (portfolio_item.quantity * portfolio_item.average_cost) + total_cost
            portfolio_item.quantity += trade_req.quantity
            portfolio_item.average_cost = total_value / portfolio_item.quantity
        else:
            portfolio_item = Portfolio(
                user_id=user.id,
                symbol=trade_req.symbol.upper(),
                quantity=trade_req.quantity,
                average_cost=current_price
            )
            db.add(portfolio_item)

    elif trade_req.transaction_type == "SELL":
        portfolio_item = db.query(Portfolio).filter(
            Portfolio.user_id == user.id, 
            Portfolio.symbol == trade_req.symbol.upper()
        ).first()

        if not portfolio_item or portfolio_item.quantity < trade_req.quantity:
            raise HTTPException(status_code=400, detail="Yetersiz hisse senedi miktarı")

        user.balance += total_cost
        portfolio_item.quantity -= trade_req.quantity

        if portfolio_item.quantity == 0:
            db.delete(portfolio_item)
    else:
        raise HTTPException(status_code=400, detail="Geçersiz işlem tipi")

    transaction = Transaction(
        user_id=user.id,
        symbol=trade_req.symbol.upper(),
        transaction_type=trade_req.transaction_type,
        quantity=trade_req.quantity,
        price=current_price
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return transaction