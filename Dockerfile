# Dockerfile for the FastAPI API service
# Deployed on Google Cloud Run (Always Free tier)

FROM python:3.11-slim

# Install git (required for cloning repos and git operations)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Cloud Run injects PORT env var; default to 8080
ENV PORT=8080

# Non-root user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Start the FastAPI server
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT} --workers 1
