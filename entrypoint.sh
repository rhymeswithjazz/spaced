#!/bin/sh
set -e

echo "Running database migrations..."
uv run python manage.py migrate --noinput

echo "Starting gunicorn..."
exec uv run gunicorn --bind 0.0.0.0:8000 --workers 2 config.wsgi:application
