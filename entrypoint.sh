#!/bin/sh
set -e

echo "Creating logs directory..."
mkdir -p /app/logs

echo "Running database migrations..."
uv run python manage.py migrate --noinput

echo "Starting supervisor (gunicorn + supercronic)..."
exec /usr/bin/supervisord -c /app/supervisord.conf
