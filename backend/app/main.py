from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.api.v1 import auth, market, trading, portfolio as portfolio_api, news, coach, behavior, stress, chat
import time
import uuid
from fastapi import Request
from loguru import logger
import sys
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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
app.include_router(behavior.router, prefix="/api/v1/behavior", tags=["behavior"])
app.include_router(stress.router, prefix="/api/v1/stress", tags=["stress"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])



@app.get("/")
def read_root():
    return {"message": "Portly API çalışıyor"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Renkli, JSON-uyumlu log formatı
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[request_id]}</cyan> | <level>{message}</level>",
    level="INFO",
)
logger.configure(extra={"request_id": "-"})


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()

    with logger.contextualize(request_id=request_id):
        logger.info(f"→ {request.method} {request.url.path}")
        response = await call_next(request)
        elapsed = (time.time() - start) * 1000
        status_emoji = "✓" if response.status_code < 400 else "✗"
        logger.info(f"← {status_emoji} {response.status_code} ({elapsed:.0f}ms)")

    response.headers["X-Request-ID"] = request_id
    return response

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)