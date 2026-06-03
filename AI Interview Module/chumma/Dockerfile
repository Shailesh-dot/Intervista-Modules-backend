FROM python:3.10-slim

# Install system dependencies for build, OCR, audio, and PDF utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libasound2 \
    libssl-dev \
    ca-certificates \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY Requirements.txt .
RUN pip install --no-cache-dir -r Requirements.txt

# Copy all application files
COPY . .

EXPOSE 8001

CMD ["uvicorn", "files.main:app", "--host", "0.0.0.0", "--port", "8001"]
