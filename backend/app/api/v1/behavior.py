from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services import behavioral_finance_service

router = APIRouter()


@router.get("/profile/{user_id}")
def get_behavior_profile(user_id: int, db: Session = Depends(get_db)):
    """
    Kullanıcının davranışsal finans profilini döner.
    Üç önyargı ölçer: Disposition Effect, Overconfidence, Loss Aversion.
    """
    return behavioral_finance_service.analyze_user_behavior(db=db, user_id=user_id)