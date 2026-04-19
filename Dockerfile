# LamiSema Production Dockerfile
# Multi-stage build for optimal image size

# --- Stage 1: Build & Dependencies ---
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies for build
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY pyproject.toml README.md LICENSE ./
COPY lamisema/ lamisema/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[all]"

# --- Stage 2: Runtime ---
FROM python:3.12-slim

WORKDIR /app

# Install Runtime System Dependencies:
# 1. Tesseract OCR + Nepali language pack
# 2. libgl1 (required by OpenCV/EasyOCR)
# 3. ghostscript (optional but recommended for some PDFs)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-nep \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed site-packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy source code
COPY . .
RUN pip install -e . --no-deps

# Default settings (can be overridden via ENV)
ENV PORT=9001
ENV LAMI_STORAGE_TYPE=memory

EXPOSE 9001

# Run the API server
CMD ["lamisema", "serve"]
