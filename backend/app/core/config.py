import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./portly.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "varsayilan_gizli_anahtar_degistir")
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")


settings = Settings()