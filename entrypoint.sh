#!/bin/sh
set -e

echo "Setting up directories..."
mkdir -p /app/logs /app/data
chmod 777 /app/logs /app/data

echo "Running database migrations..."
uv run python manage.py migrate --noinput

echo "Starting supervisor (gunicorn + supercronic)..."
exec /usr/bin/supervisord -c /app/supervisord.conf
