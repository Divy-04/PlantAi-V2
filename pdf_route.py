from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO
import session_store
import pdf_service

router = APIRouter()


@router.get("/export/pdf")
def export_pdf(session_id: str):
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404,
            detail="Session not found. Please re-upload your image.")

    history = session_store.get_history(session_id)

    pdf_bytes = pdf_service.generate_pdf(
        disease   = session["disease"],
        cause     = session["cause"],
        cure      = session["cure"],
        history   = history,
        image_b64 = session.get("image_b64")   # ← pass image to PDF
    )

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=plant_disease_report.pdf"}
    )
