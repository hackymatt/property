FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy shared code
COPY shared ./shared

# Install shared dependencies
RUN pip install --no-cache-dir -r shared/requirements.txt

# Copy application code
COPY scheduler ./

# Run the scheduler
CMD ["python", "main.py"]
