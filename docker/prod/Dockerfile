# Use Python 3.13 slim to match project (.python-version)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for geospatial (GDAL/PostGIS) + PostgreSQL dev headers
RUN apt-get update && apt-get install -y \
    binutils \
    libproj-dev \
    gdal-bin \
    curl \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Create non-root user matching host UID/GID (1000)
RUN groupadd -g 1000 python && \
    useradd -u 1000 -g python -m python

# Create isolated venv dir and data dirs owned by non-root user
RUN mkdir -p /opt/venv /app/staticfiles /app/media && \
    chown -R python:python /opt/venv /app/staticfiles /app/media

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Switch to non-root user for security (before installing deps)
USER python

# Configure uv/venv for runtime (as non-root user)
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_COMPILE_BYTECODE=1
ENV PATH=/opt/venv/bin:$PATH

# Install dependencies using UV (production - no dev dependencies)
RUN uv sync --frozen --no-dev

# Copy project files
COPY --chown=python:python . .

# Copy and set permissions for entrypoint script
COPY --chown=python:python scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Expose the port Django will run on
EXPOSE 8000
