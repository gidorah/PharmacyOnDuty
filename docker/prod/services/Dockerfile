# Use the official Python image
FROM python:3.13-slim

# Set the working directory
WORKDIR /app

# Install system dependencies for geospatial libraries
RUN apt-get update && apt-get install -y \
    binutils libproj-dev gdal-bin curl \
    && apt-get clean

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using UV (production - no dev dependencies)
RUN uv sync --frozen --no-dev

# Copy project files to the container
COPY . /app

# Copy and set permissions for entrypoint script
COPY scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Expose the port Django will run on
EXPOSE 8000
