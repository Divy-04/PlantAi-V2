FROM python:3.11-slim

ENV CUDA_VISIBLE_DEVICES=-1
ENV TF_CPP_MIN_LOG_LEVEL=2
ENV TF_ENABLE_ONEDNN_OPTS=0
ENV OMP_NUM_THREADS=1
ENV TF_NUM_INTRAOP_THREADS=1
ENV TF_NUM_INTEROP_THREADS=1

# System dependencies for TensorFlow + Playwright (Chromium)
RUN apt-get update && apt-get install -y \
    wget curl gcc g++ \
    libglib2.0-0 libnss3 libnspr4 \
    libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy entire project
COPY . .

# Emit a build-time warning when the bundled model is only a Git LFS pointer.
RUN python -c "from pathlib import Path; p=Path('/app/models/plant_disease_recog_model_pwp.keras'); data=p.read_bytes()[:64] if p.exists() else b''; is_zip=data[:4]==b'PK\\x03\\x04'; print('Model not bundled at build time; runtime MODEL_URL/local deploy is expected.' if not p.exists() else 'Bundled model looks valid.' if is_zip else 'WARNING: bundled model is a Git LFS pointer, not the real .keras file.')"

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
