from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import session_store
import chat_service

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message:    str
    language:   str = "en"


@router.post("/chat")
def chat(req: ChatRequest):
    session = session_store.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404,
            detail="Session not found. Please re-upload your image.")

    session_store.update_language(req.session_id, req.language)
    history = session_store.get_history(req.session_id)

    try:
        reply = chat_service.get_reply(
            disease      = session["disease"],
            cause        = session["cause"],
            cure         = session["cure"],
            language     = req.language,
            user_message = req.message,
            history      = history
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    session_store.append_turn(req.session_id, req.message, reply)
    return {"reply": reply}
