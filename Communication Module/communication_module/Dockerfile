FROM python:3.10-slim

# Install system dependencies for compiling packages and sound/speech tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    espeak-ng \
    libsndfile1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
