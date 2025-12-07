#!/bin/sh
set -e

echo "Setting up directories..."
mkdir -p /app/logs /app/data 2>/dev/null || true
chmod 777 /app/logs /app/data 2>/dev/null || true

echo "Running database migrations..."
uv run python manage.py migrate --noinput

echo "Starting supervisor (gunicorn + supercronic)..."
exec /usr/bin/supervisord -c /app/supervisord.conf
