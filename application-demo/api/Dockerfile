FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-nep \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir lamisema

ENV PORT=9001
ENV LAMI_STORAGE_TYPE=memory

EXPOSE 9001
CMD ["lamisema", "serve"]
