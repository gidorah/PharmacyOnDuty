# Use the official Python image
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for geospatial libraries
RUN apt-get update && apt-get install -y \
    binutils libproj-dev gdal-bin curl \
    && apt-get clean

# Install uv as the package manager/runner
RUN pip install --no-cache-dir uv

# Create a non-root user to run the app (standard UID 1000)
RUN groupadd -g 1000 python && \
    useradd -u 1000 -g python -m python

# Create the isolated virtual environment directory and give ownership to the user
RUN mkdir -p /opt/venv && chown python:python /opt/venv

# Configure uv to use the isolated environment
ENV UV_PROJECT_ENVIRONMENT="/opt/venv"
ENV UV_COMPILE_BYTECODE=1
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /workspace

# Default command can be overridden by docker compose
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
