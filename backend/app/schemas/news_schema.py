from pydantic import BaseModel
from datetime import datetime

class NewsResponse(BaseModel):
    title: str
    description: str | None = None
    url: str
    published_at: datetime
    sentiment_label: str
    sentiment_score: float