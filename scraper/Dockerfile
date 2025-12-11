FROM mcr.microsoft.com/playwright/python:v1.56.0-jammy

WORKDIR /app

# install Python dependencies
RUN pip install --upgrade pip
COPY scraper/requirements.txt .
RUN pip install -r requirements.txt

# Shared utilities
COPY shared ./shared
RUN pip install --no-cache-dir -r shared/requirements.txt

# Service code
COPY scraper ./

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the service
CMD ["python", "main.py"]
