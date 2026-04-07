from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
import session_store
import email_service
import pdf_service
import database

router = APIRouter()


class EmailRequest(BaseModel):
    session_id: str
    to_email:   str


@router.post("/export/email")
def export_email(req: EmailRequest):
    if "@" not in req.to_email or "." not in req.to_email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Invalid email address.")

    session = session_store.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404,
            detail="Session not found. Please re-upload your image.")

    history = session_store.get_history(req.session_id)

    # Generate PDF
    try:
        pdf_bytes = pdf_service.generate_pdf(
            disease   = session["disease"],
            cause     = session["cause"],
            cure      = session["cure"],
            history   = history,
            image_b64 = session.get("image_b64")
        )
    except Exception as e:
        pdf_bytes = None

    # Send email
    try:
        email_service.send_report_email(
            to_email  = req.to_email,
            disease   = session["disease"],
            cause     = session["cause"],
            cure      = session["cure"],
            history   = history,
            pdf_bytes = pdf_bytes
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Save email to database
    database.save_email(req.to_email, session["disease"], req.session_id)

    # Return PDF bytes so frontend can also trigger local download
    if pdf_bytes:
        return Response(
            content     = pdf_bytes,
            media_type  = "application/pdf",
            headers     = {"Content-Disposition": "attachment; filename=plant_disease_report.pdf",
                           "X-Email-Status": "sent"}
        )

    return {"message": f"Report sent to {req.to_email}"}
