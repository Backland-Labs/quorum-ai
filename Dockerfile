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

# Rebuild esbuild to fix version mismatch between host and binary
RUN cd node_modules/esbuild && bun install --force

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

# Install supercronic for user-space cron scheduling (works without root)
ARG SUPERCRONIC_VERSION=v0.2.30
ARG SUPERCRONIC_SHA256=21a665f278fd2feb95012df3d3e0de28df2d7968acd84eea47d732c521257974
RUN curl -fsSL -o /usr/local/bin/supercronic \
    "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-arm64" \
    && echo "${SUPERCRONIC_SHA256}  /usr/local/bin/supercronic" | sha256sum -c - \
    && chmod +x /usr/local/bin/supercronic

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

# Create user entries for common UIDs to support cron with Olas scaffolding
# The 'x' means no password - entries just need to exist in /etc/passwd for cron to work
# This covers: macOS (501), Linux/WSL2/Windows (1000), and some other common UIDs (500, 1001)
RUN echo "user500:x:500:500:User 500:/tmp:/bin/bash" >> /etc/passwd && \
    echo "user501:x:501:20:User 501:/tmp:/bin/bash" >> /etc/passwd && \
    echo "user1000:x:1000:1000:User 1000:/tmp:/bin/bash" >> /etc/passwd && \
    echo "user1001:x:1001:1001:User 1001:/tmp:/bin/bash" >> /etc/passwd

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
