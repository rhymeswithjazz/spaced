FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set work directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy project files
COPY . .

# Create data directory and set permissions for non-root user
RUN mkdir -p /app/data && \
    chmod -R 777 /app/data && \
    chmod -R 755 /app

# Collect static files
RUN uv run python manage.py collectstatic --noinput && \
    chmod -R 755 /app/staticfiles

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 8000

# Run entrypoint (handles migrations + gunicorn)
CMD ["/app/entrypoint.sh"]
