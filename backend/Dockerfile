# Use Python 3.12 base image with UV
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install curl for healthcheck and build tools for compiling native dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    make \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better Docker layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies using UV
RUN uv sync --frozen --no-install-project --no-dev

# Copy application code
COPY . .

# Install the application
RUN uv sync --frozen --no-dev

# Create non-root user for security with home directory
RUN groupadd -r appuser && useradd -r -g appuser -d /home/appuser -m appuser

# Make entrypoint script executable and set proper ownership
RUN chmod +x entrypoint.sh && \
    chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8716

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8716/healthcheck || exit 1

# Run the application using entrypoint script
ENTRYPOINT ["./entrypoint.sh"]
