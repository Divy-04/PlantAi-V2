import os
import hmac
import hashlib
import time
import base64
import json
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
import database

load_dotenv()

router = APIRouter(prefix="/admin")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
SECRET_KEY     = os.getenv("SECRET_KEY", "plantai-secret-key-change-this")
TOKEN_TTL      = 60 * 60 * 8   # 8 hours

security = HTTPBearer(auto_error=False)


# ── Simple token (no PyJWT dependency) ────────────────────────────────────────

def _make_token() -> str:
    payload   = json.dumps({"exp": int(time.time()) + TOKEN_TTL})
    b64       = base64.urlsafe_b64encode(payload.encode()).decode()
    sig       = hmac.new(SECRET_KEY.encode(), b64.encode(), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"


def _verify_token(token: str) -> bool:
    try:
        b64, sig = token.rsplit(".", 1)
        expected = hmac.new(SECRET_KEY.encode(), b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return False
        payload = json.loads(base64.urlsafe_b64decode(b64).decode())
        return payload["exp"] > time.time()
    except Exception:
        return False


def require_auth(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds or not _verify_token(creds.credentials):
        raise HTTPException(status_code=401, detail="Unauthorized. Please log in.")
    return True


# ── Auth ───────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    password: str


@router.post("/login")
def admin_login(req: LoginRequest):
    if req.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password.")
    return {"token": _make_token()}


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/stats")
def admin_stats(_: bool = Depends(require_auth)):
    return database.get_dashboard_stats()


@router.get("/disease-stats")
def admin_disease_stats(_: bool = Depends(require_auth)):
    return database.get_disease_stats()


# ── Predictions ────────────────────────────────────────────────────────────────

@router.get("/predictions")
def admin_predictions(_: bool = Depends(require_auth)):
    return database.get_all_predictions()


@router.delete("/predictions/{prediction_id}")
def admin_delete_prediction(prediction_id: int, _: bool = Depends(require_auth)):
    database.delete_prediction(prediction_id)
    return {"message": "Deleted."}


# ── Email Reports ──────────────────────────────────────────────────────────────

@router.get("/emails")
def admin_emails(_: bool = Depends(require_auth)):
    return database.get_all_emails()


# ── Contact Messages ───────────────────────────────────────────────────────────

@router.get("/contacts")
def admin_contacts(_: bool = Depends(require_auth)):
    return database.get_all_contacts()


@router.patch("/contacts/{contact_id}/read")
def admin_mark_read(contact_id: int, _: bool = Depends(require_auth)):
    database.mark_contact_read(contact_id)
    return {"message": "Marked as read."}


@router.delete("/contacts/{contact_id}")
def admin_delete_contact(contact_id: int, _: bool = Depends(require_auth)):
    database.delete_contact(contact_id)
    return {"message": "Deleted."}


# ── Admin HTML page ────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def admin_page():
    """Serve the admin panel HTML directly from this route."""
    with open("frontend/admin.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())
