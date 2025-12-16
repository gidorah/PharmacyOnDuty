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

# Create isolated venv dir owned by non-root user
RUN mkdir -p /opt/venv && chown python:python /opt/venv

# Configure uv/venv for runtime (before switching user)
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_COMPILE_BYTECODE=1
ENV PATH=/opt/venv/bin:$PATH

WORKDIR /app

# Copy entrypoint script before switching user
COPY scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Switch to non-root user
USER python

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default dev server command (overridable)
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
