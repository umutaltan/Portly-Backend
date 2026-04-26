from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse
from app.core.database import get_db
from app.schemas.chat_schema import ChatMessageCreate
from app.services import chat_service

router = APIRouter()


@router.post("/send")
async def send_message(payload: ChatMessageCreate, db: Session = Depends(get_db)):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Boş mesaj gönderilemez")

    if len(payload.message) > 2000:
        raise HTTPException(status_code=400, detail="Mesaj çok uzun (max 2000 karakter)")

    async def event_generator():
        try:
            # Hemen "thinking" event'i gönder ki UI feedback versin
            yield {"event": "thinking", "data": ""}
            
            for token in chat_service.stream_chat_response(
                db=db, user_id=payload.user_id, user_message=payload.message
            ):
                yield {"event": "token", "data": token}
            yield {"event": "done", "data": ""}
        except Exception as e:
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
        ping=20,
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )

@router.get("/history/{user_id}")
def get_history(user_id: int, db: Session = Depends(get_db)):
    """Kullanıcının sohbet geçmişini döndürür."""
    return chat_service.get_chat_history(db=db, user_id=user_id)


@router.delete("/history/{user_id}")
def clear_history(user_id: int, db: Session = Depends(get_db)):
    """Kullanıcının tüm sohbet geçmişini siler."""
    count = chat_service.clear_chat_history(db=db, user_id=user_id)
    return {"success": True, "deleted_count": count}