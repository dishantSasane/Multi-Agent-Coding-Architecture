#!/bin/bash
set -e

echo "Starting CodeForge application..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z db 5432; do
    sleep 0.1
done
echo "PostgreSQL is ready"

# Wait for Redis to be ready
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
    sleep 0.1
done
echo "Redis is ready"

# Run database migrations
echo "Running database migrations..."
python -m app.models.database init-db || true

# Start the application
echo "Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
