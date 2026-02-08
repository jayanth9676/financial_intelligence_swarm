FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies
# gcc and python3-dev might be needed for building some deps
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt .

# CRITICAL: Install CPU-only version of PyTorch first to avoid downloading 4GB+ CUDA binaries
# docling or fastembed might depend on torch
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port
ENV PORT=8080
EXPOSE 8080

# Run the application
# Use shell form (sh -c) to properly expand the PORT environment variable
CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker backend.main:app --bind 0.0.0.0:${PORT:-8080} --timeout 120"]
