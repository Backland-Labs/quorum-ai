# Multi-stage Dockerfile for Quorum AI Application
# Stage 1: Build frontend
FROM oven/bun:1-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend dependency files
COPY frontend/package.json frontend/bun.lock ./

# Install frontend dependencies (including dev dependencies for build)
RUN bun install

# Copy frontend source code
COPY frontend/ ./

# Build frontend for production
RUN bun run build

# Stage 2: Backend with built frontend
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Set environment variables for UV and Python
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_CACHE_DIR=/app/.cache/uv
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

# Create cache directory early with proper permissions
RUN mkdir -p /app/.cache/uv

# Install Python dependencies using UV
RUN uv sync --frozen --no-install-project --no-dev

# Copy backend application code
COPY backend/ ./

# Install the backend application
RUN uv sync --frozen --no-dev

# Copy built frontend files from stage 1
COPY --from=frontend-builder /app/frontend/build ./static/

# Create necessary directories and set permissions
RUN mkdir -p /app/logs && \
    chmod +x entrypoint.sh && \
    chmod -R 777 /app

# Expose the application port
EXPOSE 8716

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8716/healthcheck || exit 1

# Use the existing entrypoint script
ENTRYPOINT ["./entrypoint.sh"]
