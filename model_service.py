import json
import numpy as np
import tensorflow as tf
from image_utils import preprocess_image_variants, set_image_size
import plantnet_service

MODEL_PATH = "models/plant_disease_recog_model_pwp.keras"
JSON_PATH  = "plant_disease.json"
BACKGROUND_CLASS_NAME = "Background_without_leaves"
BACKGROUND_REJECT_CONFIDENCE = 85.0
BACKGROUND_REJECT_MARGIN = 25.0
BACKGROUND_RESCUE_CONFIDENCE = 35.0

_model   = None
_classes = []


def _find_class_index(class_name: str) -> int:
    for i, entry in enumerate(_classes):
        if entry["name"] == class_name:
            return i
    return -1


def load_model():
    global _model, _classes

    print("Loading model...")
    _model = tf.keras.models.load_model(MODEL_PATH)

    # ── Read actual input shape from the model ─────────────────────────
    # input_shape is (None, H, W, C) — index 1 and 2 are H and W
    input_shape = _model.input_shape
    print(f"Model input shape: {input_shape}")

    h = input_shape[1]
    w = input_shape[2]

    if h and w:
        # Model has a fixed input size — use it exactly
        set_image_size(h, w)
    else:
        # Model accepts dynamic input (global pooling) — use safe default
        print("⚠️  Model has dynamic input shape — defaulting to 224×224")
        set_image_size(224, 224)

    # ── Load class labels ──────────────────────────────────────────────
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        _classes = json.load(f)

    num_outputs = _model.output_shape[-1]
    print(f"Model output classes : {num_outputs}")
    print(f"JSON entries         : {len(_classes)}")

    if num_outputs != len(_classes):
        print(f"⚠️  WARNING: model has {num_outputs} outputs but JSON has {len(_classes)} entries.")


def predict(image_bytes: bytes) -> dict:
    """
    Combined prediction pipeline:
      1. PlantNet API  → identify plant species and add metadata
      2. Local TF model → predict disease class
      3. Merge into a single response dict
    """
    if _model is None:
        raise RuntimeError("Model is not loaded yet.")

    # ── Step 1: PlantNet metadata (soft signal, not a hard gate) ──────
    plant_info = plantnet_service.identify_plant(image_bytes)

    # ── Step 2: Disease prediction ─────────────────────────────────────
    arr_batch = preprocess_image_variants(image_bytes)
    preds_batch = _model.predict(arr_batch, verbose=0)
    preds = np.mean(preds_batch, axis=0)   # shape: (num_classes,)

    sorted_indices = np.argsort(preds)[::-1]
    idx            = int(sorted_indices[0])
    confidence     = float(preds[idx]) * 100
    background_idx = _find_class_index(BACKGROUND_CLASS_NAME)

    # Top-3 predictions
    top3_indices = sorted_indices[:3]
    top3 = [
        {
            "name":       _classes[i]["name"],
            "confidence": round(float(preds[i]) * 100, 2),
        }
        for i in top3_indices if i < len(_classes)
    ]

    margin = confidence - (float(preds[sorted_indices[1]]) * 100 if len(sorted_indices) > 1 else 0.0)
    low_confidence = confidence < 60.0 or (confidence < 90.0 and margin < 12.0)

    rescued_from_background = False
    if idx == background_idx and background_idx != -1:
        non_background_idx = next((int(i) for i in sorted_indices if int(i) != background_idx), background_idx)
        non_background_confidence = float(preds[non_background_idx]) * 100 if non_background_idx != background_idx else 0.0
        plant_verified = bool(plant_info.get("verified"))
        plant_detected = bool(plant_info.get("is_plant"))

        should_use_non_background = (
            non_background_idx != background_idx and (
                (plant_verified and plant_detected and non_background_confidence >= 20.0) or
                (non_background_confidence >= BACKGROUND_RESCUE_CONFIDENCE)
            )
        )

        if should_use_non_background:
            idx = non_background_idx
            confidence = non_background_confidence
            rescued_from_background = True
            low_confidence = True
        elif confidence >= BACKGROUND_REJECT_CONFIDENCE and margin >= BACKGROUND_REJECT_MARGIN:
            return {
                "is_plant": False,
                "rejected": True,
                "message": (
                    "The image does not show a clear leaf. "
                    "Please upload a close-up photo of a single plant leaf."
                ),
                "confidence": round(confidence, 2),
                "class_index": idx,
                "top3": top3,
            }
        elif non_background_idx != background_idx:
            idx = non_background_idx
            confidence = non_background_confidence
            rescued_from_background = True
            low_confidence = True

    if idx >= len(_classes):
        disease_name = f"Unknown_class_{idx}"
        cause        = "This class is not mapped in plant_disease.json yet."
        cure         = "Please add this class entry to plant_disease.json."
    else:
        entry        = _classes[idx]
        disease_name = entry["name"]
        cause        = entry["cause"]
        cure         = entry["cure"]

    # ── Step 3: Merge & return ─────────────────────────────────────────
    return {
        "is_plant":          bool(plant_info["is_plant"]),
        "rejected":          False,

        # From PlantNet
        "plantnet_verified": plant_info.get("verified", False),
        "plant_common_name": plant_info["common_name"],
        "plant_species":     plant_info["species"],
        "plant_family":      plant_info["family"],
        "plantnet_score":    plant_info["score"],
        "plantnet_unverified": not plant_info.get("verified", False),

        # From local model
        "name":              disease_name,
        "cause":             cause,
        "cure":              cure,
        "confidence":        round(confidence, 2),
        "class_index":       idx,
        "low_confidence":    low_confidence,
        "rescued_from_background": rescued_from_background,
        "top3":              top3,
    }
