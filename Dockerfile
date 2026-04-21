FROM python:3.11-slim

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

# If a model file is present during build, verify it is a real .keras zip and not a Git LFS pointer.
RUN python -c "from pathlib import Path; import sys; p=Path('/app/models/plant_disease_recog_model_pwp.keras'); data=p.read_bytes()[:64] if p.exists() else b''; is_zip=data[:4]==b'PK\\x03\\x04'; is_lfs=data.startswith(b'version https://git-lfs.github.com/spec/v1'); print('Model not bundled at build time; runtime MODEL_URL/local deploy is expected.' if not p.exists() else 'Bundled model looks valid.' if is_zip else 'Bundled model is a Git LFS pointer, not the real .keras file.'); sys.exit(0 if (not p.exists()) or is_zip else 1)"

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
