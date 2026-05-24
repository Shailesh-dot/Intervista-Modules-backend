# Use official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables for optimization
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files
# PYTHONUNBUFFERED: Ensures that Python output is logged to the terminal
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy requirement files first to leverage Docker cache
COPY requirements.txt .

# Install dependencies and update pip
# Note: We pip install gunicorn directly here to ensure the production HTTP engine is available
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Copy the rest of the application codebase
COPY . .

# Expose the application port
EXPOSE 8000

# --- Production Tuning ---
# Because FastAPI is highly asynchronous, it scales incredibly well for I/O bound tasks
# (like querying Supabase and waiting for Judge0 responses).
# 4 Uvicorn workers wrapped in Gunicorn is an industry-standard baseline that can easily
# handle 200-250 concurrent users, especially on a 2-core or 4-core VM.
ENV WORKERS=4

# Boot the application using Gunicorn process manager with Uvicorn worker class
CMD gunicorn app.main:app --workers ${WORKERS} --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
