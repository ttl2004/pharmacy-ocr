# OCR service (FastAPI), chỉ dùng engine Google Vision: không cài torch / vietocr.
# Biến môi trường không nằm trong image: docker compose đọc từ .env của repo này (env_file).
FROM python:3.11-slim

# opencv-contrib-python cần libGL và glib.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Cài editable để ROOT_DIR trong config trỏ về /app như khi chạy trên máy.
COPY pyproject.toml ./
COPY src ./src
RUN pip install -e .

COPY . .

# SQLite và ảnh của các lần trích xuất (gắn volume trong compose).
ENV DATA_DIR=/data \
    OCR_ENGINE=vision
RUN mkdir -p /data

EXPOSE 8000
CMD ["uvicorn", "ocr_baseline.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
