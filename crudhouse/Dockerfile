FROM python:3.12-slim

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/usr/src/app:$PYTHONPATH

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# install Python dependencies
RUN pip install --upgrade pip
COPY crudhouse/requirements.txt .
RUN pip install -r requirements.txt

# Copy shared code
COPY shared ./shared

# Install shared dependencies
RUN pip install -r shared/requirements.txt

# copy project
COPY crudhouse ./crudhouse

EXPOSE 8000

# run entrypoint.sh - convert line endings and make executable
RUN sed -i 's/\r$//' ./crudhouse/entrypoint.sh && chmod +x ./crudhouse/entrypoint.sh

ENTRYPOINT ["./crudhouse/entrypoint.sh"]
