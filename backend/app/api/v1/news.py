from fastapi import APIRouter
from typing import List
from app.schemas.news_schema import NewsResponse
from app.services import nlp_sentiment_service

router = APIRouter()


@router.get("/latest", response_model=List[NewsResponse])
def get_latest_news(query: str = "stock market", force: bool = False):
    """
    En güncel finansal haberleri VADER sentiment analizi ile birlikte döndürür.
    force=true verilirse cache'i bypass eder.
    """
    return nlp_sentiment_service.get_financial_news(query=query, force_refresh=force)