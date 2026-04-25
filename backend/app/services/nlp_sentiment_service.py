import requests
from fastapi import HTTPException
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime, timedelta
from app.core.config import settings

analyzer = SentimentIntensityAnalyzer()

# Cache sistemi
_news_cache = {"data": None, "timestamp": None, "query": None}
_NEWS_CACHE_TTL_MINUTES = 15


def analyze_sentiment(text: str) -> dict:
    if not text:
        return {"label": "Nötr", "score": 0.0}
    
    scores = analyzer.polarity_scores(text)
    compound = scores['compound']
    
    if compound >= 0.05:
        label = "Pozitif"
    elif compound <= -0.05:
        label = "Negatif"
    else:
        label = "Nötr"
        
    return {"label": label, "score": compound}


def get_financial_news(query: str = "stock market", force_refresh: bool = False):
    if not settings.NEWS_API_KEY:
        raise HTTPException(status_code=500, detail="NEWS_API_KEY .env dosyasında bulunamadı")

    now = datetime.now()
    
    if (not force_refresh
            and _news_cache["data"] is not None
            and _news_cache["query"] == query
            and _news_cache["timestamp"] is not None
            and now - _news_cache["timestamp"] < timedelta(minutes=_NEWS_CACHE_TTL_MINUTES)):
        return _news_cache["data"]

    url = (
        "https://newsapi.org/v2/everything"
        f"?q={query}"
        "&domains=bloomberg.com,reuters.com,cnbc.com,marketwatch.com,finance.yahoo.com,ft.com,wsj.com"
        "&language=en"
        "&sortBy=publishedAt"
        f"&apiKey={settings.NEWS_API_KEY}"
    )
    response = requests.get(url)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"NewsAPI Hatası: {response.text}")
        
    articles = response.json().get("articles", [])[:10]
    news_list = []
    
    for article in articles:
        text_to_analyze = f"{article.get('title', '')} {article.get('description', '')}"
        sentiment = analyze_sentiment(text_to_analyze)
        
        pub_date_str = article.get("publishedAt")
        try:
            pub_date = datetime.strptime(pub_date_str, "%Y-%m-%dT%H:%M:%SZ") if pub_date_str else datetime.now()
        except ValueError:
            pub_date = datetime.now()

        news_list.append({
            "title": article.get("title", "Başlık Yok"),
            "description": article.get("description", ""),
            "url": article.get("url", ""),
            "published_at": pub_date,
            "sentiment_label": sentiment["label"],
            "sentiment_score": sentiment["score"]
        })
    
    # Cache'e kaydet
    _news_cache["data"] = news_list
    _news_cache["timestamp"] = now
    _news_cache["query"] = query
    
    return news_list