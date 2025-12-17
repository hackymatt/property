FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Shared utilities
COPY shared ./shared
RUN pip install --no-cache-dir -r shared/requirements.txt

# Service code
COPY data_ingestion ./

CMD ["python", "main.py"]
