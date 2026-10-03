FROM python:3.12-slim
# OCR (Arabic + English) and PDF page rendering for scanned documents
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng \
    poppler-utils libglib2.0-0 fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml .
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
RUN pip install --no-cache-dir .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
