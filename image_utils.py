import numpy as np
from PIL import Image
import io

IMG_SIZE = (160, 160)

def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """
    Converts raw image bytes → model-ready numpy array.
    Shape: (1, 224, 224, 3), values: 0.0 to 1.0
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize(IMG_SIZE)
    arr = np.array(img, dtype=np.float32)   # no normalization — model trained on raw 0-255 values
    return np.expand_dims(arr, axis=0)
