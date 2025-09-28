# Multi-stage Docker build for ProcessGuard
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --only=production
COPY frontend/ ./
RUN npm run build

# Python backend stage
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    procps \
    net-tools \
    lsof \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash processguard

# Set working directory
WORKDIR /app

# Copy Python requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/ ./backend/

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Create necessary directories
RUN mkdir -p /app/logs /app/config /app/data && \
    chown -R processguard:processguard /app

# Copy configuration template
COPY configs/config.example.json /app/config/config.json

# Switch to non-root user
USER processguard

# Expose ports
EXPOSE 7500

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:7500/api/v1/health || exit 1

# Default command
CMD ["python", "-m", "backend.src.api.main", "--config", "/app/config/config.json", "--host", "0.0.0.0", "--port", "7500"]