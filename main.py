from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import model_service, session_store, database
from chat_route    import router as chat_router
from pdf_route     import router as pdf_router
from email_route   import router as email_router
from contact_route import router as contact_router
from admin_route   import router as admin_router

LOAD_MODEL_ON_STARTUP = os.getenv("LOAD_MODEL_ON_STARTUP", "false").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("App startup: begin")
    if LOAD_MODEL_ON_STARTUP:
        print("App startup: eager model load enabled")
        model_service.load_model()
    else:
        print("App startup: model load deferred until first prediction request")
    print("App startup: initializing database")
    database.init_db()
    print("App startup: complete")
    yield


app = FastAPI(title="PlantAI API", version="6.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

app.include_router(chat_router)
app.include_router(pdf_router)
app.include_router(email_router)
app.include_router(contact_router)
app.include_router(admin_router)


@app.get("/api/health")
def health():
    return {"status": "PlantAI API running ✅"}


@app.post("/predict")
async def predict_disease(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"Expected an image file, got: {file.content_type}"
        )

    image_bytes = await file.read()

    try:
        result = model_service.predict(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    # ── Non-plant image → reject early ────────────────────────────────
    if result.get("rejected"):
        raise HTTPException(status_code=422, detail=result["message"])

    # ── Valid plant → create session ───────────────────────────────────
    session_id = session_store.create_session(
        disease     = result["name"],
        cause       = result["cause"],
        cure        = result["cure"],
        image_bytes = image_bytes,
    )
    result["session_id"] = session_id

    # ── Save prediction to DB ──────────────────────────────────────────
    database.save_prediction(
        session_id        = session_id,
        disease           = result["name"],
        confidence        = result["confidence"],
        plant_common_name = result.get("plant_common_name", ""),
        plant_species     = result.get("plant_species", ""),
        low_confidence    = result.get("low_confidence", False),
    )

    return result


app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
