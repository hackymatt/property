FROM python:3.11-slim

WORKDIR /app

# Shared utilities
COPY shared ./shared
RUN pip install --no-cache-dir -r shared/requirements.txt

# Service code
COPY logger ./

CMD ["python", "main.py"]
