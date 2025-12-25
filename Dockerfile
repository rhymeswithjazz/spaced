FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1

# Install system dependencies including supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install supercronic (lightweight cron for containers)
ARG SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.29/supercronic-linux-amd64
ARG SUPERCRONIC_SHA1SUM=cd48d45c4b10f3f0bfdd3a57d054cd05ac96812b
RUN curl -fsSLO "$SUPERCRONIC_URL" \
    && echo "${SUPERCRONIC_SHA1SUM}  supercronic-linux-amd64" | sha1sum -c - \
    && chmod +x supercronic-linux-amd64 \
    && mv supercronic-linux-amd64 /usr/local/bin/supercronic

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

# Create data and logs directories
RUN mkdir -p /app/data /app/logs

# Collect static files
RUN uv run python manage.py collectstatic --noinput

# Make entrypoint executable and set permissions for non-root user
# This ensures the container can run as any user (e.g., user: "1026:100" in Portainer)
RUN chmod +x /app/entrypoint.sh && \
    chmod -R 755 /app && \
    chmod -R 777 /app/data /app/logs /app/.venv

# Expose port
EXPOSE 8000

# Run entrypoint (handles migrations + supervisor)
CMD ["/app/entrypoint.sh"]
