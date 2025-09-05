# Single stage Dockerfile for Quorum AI Application
# Uses pre-built frontend files to avoid build issues

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Set environment variables for UV and Python
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies for backend
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    make \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy backend dependency files first for better Docker layer caching
COPY backend/pyproject.toml backend/uv.lock ./

# Install Python dependencies using UV
RUN uv sync --frozen --no-install-project --no-dev

# Copy backend application code
COPY backend/ ./

# Install the backend application
RUN uv sync --frozen --no-dev

# Copy pre-built frontend files
COPY frontend/build/client ./static/

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -d /home/appuser -m appuser

# Create necessary directories and set permissions
RUN mkdir -p /app/logs && \
    chmod +x entrypoint.sh && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 8716

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8716/healthcheck || exit 1

# Use the existing entrypoint script
ENTRYPOINT ["./entrypoint.sh"]
