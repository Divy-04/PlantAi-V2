import uuid
import base64
from typing import Optional

_sessions: dict = {}


def create_session(disease: str, cause: str, cure: str,
                   language: str = "en", image_bytes: bytes = None) -> str:
    session_id = str(uuid.uuid4())

    # Convert image to base64 so it can be embedded in PDF HTML
    image_b64 = None
    if image_bytes:
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    _sessions[session_id] = {
        "disease":   disease,
        "cause":     cause,
        "cure":      cure,
        "language":  language,
        "image_b64": image_b64,
        "history":   []
    }
    return session_id


def get_session(session_id: str) -> Optional[dict]:
    return _sessions.get(session_id)


def update_language(session_id: str, language: str):
    if session_id in _sessions:
        _sessions[session_id]["language"] = language


def append_turn(session_id: str, user_msg: str, ai_msg: str):
    if session_id in _sessions:
        _sessions[session_id]["history"].append({"role": "user",  "content": user_msg})
        _sessions[session_id]["history"].append({"role": "model", "content": ai_msg})


def get_history(session_id: str) -> list:
    return _sessions.get(session_id, {}).get("history", [])
