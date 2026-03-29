from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user_schema import UserCreate
import bcrypt

def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)
    return hashed_password.decode('utf-8')

def create_user(db: Session, user: UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        balance=100000.0
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user