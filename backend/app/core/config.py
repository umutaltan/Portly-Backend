import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Portly"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./portly.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey")
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
    FIREBASE_SERVICE_ACCOUNT_PATH: str = os.path.join(os.getcwd(), "firebase-adminsdk.json")

settings = Settings()