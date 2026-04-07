from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import re
import database

router = APIRouter()


class ContactRequest(BaseModel):
    name:    str
    email:   str
    phone:   str
    subject: str = ""
    message: str


@router.post("/contact")
def submit_contact(req: ContactRequest):
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Name is required.")
    if "@" not in req.email:
        raise HTTPException(status_code=400, detail="Invalid email address.")
    if not req.phone.strip():
        raise HTTPException(status_code=400, detail="Phone number is required.")
    if not re.fullmatch(r"\d{10}", req.phone.strip()):
        raise HTTPException(status_code=400, detail="Phone number must be exactly 10 digits.")
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message is required.")

    database.save_contact(req.name, req.email, req.phone, req.subject, req.message)
    return {"message": "Thank you! Your message has been received."}
