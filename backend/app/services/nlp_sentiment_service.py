import requests
from fastapi import HTTPException
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime
from app.core.config import settings

analyzer = SentimentIntensityAnalyzer()

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

def get_financial_news(query: str = "finance"):
    if not settings.NEWS_API_KEY:
        raise HTTPException(status_code=500, detail="NEWS_API_KEY .env dosyasında bulunamadı")

    url = f"https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&apiKey={settings.NEWS_API_KEY}"
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
        
    return news_list