from fastapi import FastAPI
from app.core.database import engine, Base
from app.api.v1 import auth, market, trading, portfolio as portfolio_api, news

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Portly API",
    description="AI Destekli Sanal Borsa ve Finansal Eğitim Platformu",
    version="1.0.0"
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(market.router, prefix="/api/v1/market", tags=["market"])
app.include_router(trading.router, prefix="/api/v1/trading", tags=["trading"])
app.include_router(portfolio_api.router, prefix="/api/v1/portfolio", tags=["portfolio"])
app.include_router(news.router, prefix="/api/v1/news", tags=["news"])

@app.get("/")
def read_root():
    return {"message": "Portly API çalışıyor"}