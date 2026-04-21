import numpy as np
from PIL import Image, ImageOps
import io

# Set dynamically at startup from model.input_shape — do NOT hardcode this
_IMG_H = 224
_IMG_W = 224


def set_image_size(height: int, width: int):
    """Called by model_service.load_model() after the model is loaded."""
    global _IMG_H, _IMG_W
    _IMG_H = height
    _IMG_W = width
    print(f"✅ Image preprocessing set to {_IMG_H}×{_IMG_W}")


def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """Backward-compatible single-variant preprocessing."""
    return preprocess_image_variants(image_bytes)[:1]


def preprocess_image_variants(image_bytes: bytes) -> np.ndarray:
    """
    Converts raw image bytes to a small batch of model-ready variants.

    This helps a PlantVillage-style model handle more natural web photos by
    trying a few different crops/resizing strategies and averaging them.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    stretched = img.resize((_IMG_W, _IMG_H), Image.LANCZOS)

    contained = ImageOps.contain(img, (_IMG_W, _IMG_H), Image.LANCZOS)
    padded = Image.new("RGB", (_IMG_W, _IMG_H), (0, 0, 0))
    x = (_IMG_W - contained.width) // 2
    y = (_IMG_H - contained.height) // 2
    padded.paste(contained, (x, y))

    cropped = ImageOps.fit(
        img,
        (_IMG_W, _IMG_H),
        method=Image.LANCZOS,
        centering=(0.5, 0.5),
    )

    variants = [stretched, padded, cropped]
    arr = np.stack([np.array(variant, dtype=np.float32) for variant in variants], axis=0)
    return arr
