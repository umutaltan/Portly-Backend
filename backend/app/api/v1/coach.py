from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services import ai_coach_service

router = APIRouter()


@router.get("/advice/{user_id}")
def get_portfolio_advice(user_id: int, db: Session = Depends(get_db)):
    """Kullanıcının portföyüne özel AI koçluk tavsiyesi üretir."""
    return ai_coach_service.generate_portfolio_advice(db=db, user_id=user_id)