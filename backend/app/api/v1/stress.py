from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services import stress_test_service

router = APIRouter()


@router.get("/scenarios")
def get_scenarios():
    """Mevcut stres testi senaryolarının listesi."""
    return stress_test_service.list_scenarios()


@router.get("/run/{user_id}")
def run_stress_test(
    user_id: int,
    scenario: str = "normal",
    db: Session = Depends(get_db),
):
    """
    Belirtilen kullanıcı portföyü için Monte Carlo stres testi çalıştırır.
    scenario: normal, subprime_2008, covid_2020, bist_2018, black_swan
    """
    return stress_test_service.run_monte_carlo(
        db=db, user_id=user_id, scenario=scenario
    )