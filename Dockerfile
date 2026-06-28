FROM python:3.11-slim

# Install system deps for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV HOST=0.0.0.0
ENV DEBUG=false

EXPOSE 10000

# Use gunicorn for production, fallback to flask dev server
CMD gunicorn app:server --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 2 --timeout 120
