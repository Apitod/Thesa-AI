# ============================================================
# Thesa Python API — Dockerfile
# Digunakan untuk service thesa-api DAN thesa-worker
# ============================================================

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Variabel lingkungan
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (dari root Backend requirements dulu, lalu python_api)
COPY requirements.txt /app/requirements.txt
COPY python_api/requirements.txt /app/python_api/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt \
    && pip install --no-cache-dir -r /app/python_api/requirements.txt

# Copy source code
COPY src/ /app/src/
COPY sinta_finder/ /app/sinta_finder/
COPY templates/ /app/templates/
COPY data/ /app/data/
COPY python_api/ /app/python_api/

# Buat direktori output
RUN mkdir -p /app/output

# Port default untuk FastAPI
EXPOSE 8000

# Default command: jalankan FastAPI (bisa di-override untuk Celery worker)
CMD ["uvicorn", "python_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
