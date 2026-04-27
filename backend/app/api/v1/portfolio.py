from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.services import portfolio_service
from app.schemas.portfolio_schema import PortfolioItemResponse

router = APIRouter()

@router.get("/{user_id}", response_model=List[PortfolioItemResponse])
def get_portfolio(user_id: int, db: Session = Depends(get_db)):
    return portfolio_service.get_user_portfolio(db=db, user_id=user_id)
@router.get("/{user_id}/sectors")
def get_portfolio_sectors(user_id: int, db: Session = Depends(get_db)):
    return portfolio_service.get_sector_breakdown(db=db, user_id=user_id)