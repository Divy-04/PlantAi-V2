import json
import numpy as np
import tensorflow as tf
from image_utils import preprocess_image

MODEL_PATH = "models/plant_disease_recog_model_pwp.keras"
JSON_PATH  = "plant_disease.json"

_model   = None
_classes = []


def load_model():
    global _model, _classes

    print("Loading model...")
    _model = tf.keras.models.load_model(MODEL_PATH)
    print(f"Model loaded. Input shape: {_model.input_shape}")

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        _classes = json.load(f)

    num_outputs = _model.output_shape[-1]
    print(f"Model output classes : {num_outputs}")
    print(f"JSON entries         : {len(_classes)}")

    if num_outputs != len(_classes):
        print(f"WARNING: model has {num_outputs} outputs but JSON has {len(_classes)} entries.")


def predict(image_bytes: bytes) -> dict:
    if _model is None:
        raise RuntimeError("Model is not loaded yet.")

    arr   = preprocess_image(image_bytes)
    preds = _model.predict(arr, verbose=0)

    idx        = int(np.argmax(preds[0]))
    confidence = float(np.max(preds[0])) * 100

    if idx >= len(_classes):
        return {
            "name":        f"Unknown_class_{idx}",
            "cause":       "This class is not mapped in plant_disease.json yet.",
            "cure":        "Please add this class entry to plant_disease.json.",
            "confidence":  round(confidence, 2),
            "class_index": idx,
        }

    disease = _classes[idx]

    return {
        "name":        disease["name"],
        "cause":       disease["cause"],
        "cure":        disease["cure"],
        "confidence":  round(confidence, 2),
        "class_index": idx,
    }
