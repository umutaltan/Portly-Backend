from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.api.v1 import auth, market, trading, portfolio as portfolio_api, news , coach

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Portly API",
    description="AI Destekli Sanal Borsa ve Finansal Eğitim Platformu",
    version="1.0.0"
)

# CORS — Flutter web + dev için şart
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # prod'da spesifik domain yazılacak
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(market.router, prefix="/api/v1/market", tags=["market"])
app.include_router(trading.router, prefix="/api/v1/trading", tags=["trading"])
app.include_router(portfolio_api.router, prefix="/api/v1/portfolio", tags=["portfolio"])
app.include_router(news.router, prefix="/api/v1/news", tags=["news"])
app.include_router(coach.router, prefix="/api/v1/coach", tags=["coach"])



@app.get("/")
def read_root():
    return {"message": "Portly API çalışıyor"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}