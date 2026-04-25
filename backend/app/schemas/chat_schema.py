from pydantic import BaseModel
from datetime import datetime


class ChatMessageCreate(BaseModel):
    user_id: int
    message: str


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True