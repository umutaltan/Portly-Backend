import random
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.schemas.trade_schema import TradeRequest
from app.services.market_data_service import get_stock_data
from app.services import market_data_service
from datetime import datetime, timedelta

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


def generate_demo_trades(db: Session, user_id: int, count: int = 8):
    """
    Yeni kullanıcı için demo işlem geçmişi üretir.
    Davranışsal profilin çalışması için karışık BUY/SELL akışı oluşturur.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    # Mevcut işlemleri sil (demo reset için)
    db.query(Transaction).filter(Transaction.user_id == user_id).delete()

    # Bakiyeyi sıfırla
    user.balance = 100000.0

    symbols = ["AAPL", "TSLA", "THYAO.IS", "ASELS.IS", "MSFT", "NVDA"]
    now = datetime.utcnow()

    trades_created = []
    holdings = {}  # sym -> qty

    for i in range(count):
        # Geçmişe doğru tarih (son 30 gün)
        days_ago = random.randint(1, 30)
        timestamp = now - timedelta(days=days_ago, hours=random.randint(0, 23))

        # Eğer hiç hisse yoksa BUY yap; varsa %60 BUY, %40 SELL
        if not holdings or random.random() < 0.6:
            sym = random.choice(symbols)
            try:
                price_data = market_data_service.get_stock_data(sym)
                price = price_data["current_price"] * random.uniform(0.85, 1.05)
            except Exception:
                price = random.uniform(50, 300)

            qty = random.choice([5, 10, 15, 20, 25])
            cost = price * qty

            if user.balance >= cost:
                user.balance -= cost
                holdings[sym] = holdings.get(sym, 0) + qty
                tx = Transaction(
                    user_id=user_id,
                    symbol=sym,
                    transaction_type="BUY",
                    quantity=qty,
                    price=round(price, 2),
                    timestamp=timestamp,
                )
                db.add(tx)
                trades_created.append({"type": "BUY", "symbol": sym, "qty": qty, "price": round(price, 2)})
        else:
            # SELL: elinde olan bir hisseden sat
            sym = random.choice(list(holdings.keys()))
            qty_held = holdings[sym]
            if qty_held <= 0:
                continue
            qty_to_sell = random.randint(1, max(1, qty_held // 2))
            try:
                price_data = market_data_service.get_stock_data(sym)
                price = price_data["current_price"] * random.uniform(0.9, 1.15)
            except Exception:
                price = random.uniform(50, 300)

            user.balance += price * qty_to_sell
            holdings[sym] -= qty_to_sell
            if holdings[sym] <= 0:
                del holdings[sym]
            tx = Transaction(
                user_id=user_id,
                symbol=sym,
                transaction_type="SELL",
                quantity=qty_to_sell,
                price=round(price, 2),
                timestamp=timestamp,
            )
            db.add(tx)
            trades_created.append({"type": "SELL", "symbol": sym, "qty": qty_to_sell, "price": round(price, 2)})

    db.commit()

    return {
        "success": True,
        "trades_created": len(trades_created),
        "trades": trades_created,
        "final_balance": round(user.balance, 2),
    }