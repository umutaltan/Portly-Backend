from fastapi import APIRouter
from typing import List
from app.schemas.news_schema import NewsResponse
from app.services import nlp_sentiment_service

router = APIRouter()

@router.get("/latest", response_model=List[NewsResponse])
def get_latest_news(query: str = "finance"):
    return nlp_sentiment_service.get_financial_news(query=query)