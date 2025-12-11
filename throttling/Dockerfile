FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy shared code
COPY shared ./shared

# Install shared dependencies (includes redis)
RUN pip install --no-cache-dir -r shared/requirements.txt

# Copy application code
COPY throttling ./

# Run the throttling service
CMD ["python", "main.py"]
