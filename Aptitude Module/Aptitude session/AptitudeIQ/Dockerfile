FROM python:3.10-slim

# Install system dependencies for database connection and OCR tasks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install required python libraries
RUN pip install --no-cache-dir \
    flask \
    flask-cors \
    psycopg2-binary \
    pdfplumber \
    pytesseract \
    opencv-python-headless \
    requests

COPY . .

EXPOSE 5000

CMD ["python", "server.py"]
