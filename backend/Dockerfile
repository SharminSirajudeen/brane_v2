# =============================================================================
# BRANE Backend - Production Dockerfile for Fly.io
# Multi-stage build optimized for small image size and fast cold starts
# =============================================================================

# =============================================================================
# STAGE 1: BUILDER
# Purpose: Compile dependencies and build artifacts in isolation
# Why: Separates build tools from runtime, reduces final image size by ~40%
# =============================================================================

FROM python:3.10-slim AS builder

# WORKDIR: Set working directory for all subsequent commands
# Why: Provides a consistent base path for COPY and RUN commands
# Impact: All relative paths are resolved from /app
WORKDIR /app

# Install build dependencies required for compiling Python packages
# gcc: C compiler for packages with C extensions (e.g., psycopg2, cryptography)
# g++: C++ compiler for packages with C++ extensions
# libpq-dev: PostgreSQL client library headers (required for psycopg2)
# python3-dev: Python header files for building native extensions
# --no-install-recommends: Skip optional packages to minimize image size (~100MB saved)
# && rm -rf /var/lib/apt/lists/*: Clean up apt cache to save ~30MB in this layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a Python virtual environment to isolate dependencies
# Why: Makes it easy to copy only the installed packages to the final stage
# Alternative: Install globally (messier, harder to isolate)
RUN python -m venv /opt/venv

# Activate the virtual environment for all subsequent RUN commands
# Why: Ensures pip installs packages into /opt/venv, not globally
# Mechanism: Prepends /opt/venv/bin to PATH
ENV PATH="/opt/venv/bin:$PATH"

# Copy only requirements.txt first (before application code)
# Why: Docker layer caching - this layer only rebuilds if requirements.txt changes
# Impact: Saves 2-5 minutes on rebuilds when only code changes
COPY requirements.txt .

# Install Python dependencies into the virtual environment
# --no-cache-dir: Don't cache pip downloads (~200MB saved)
# --upgrade: Ensure pip itself is up-to-date (avoids warnings)
# Why: Compile all dependencies with build tools available
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# =============================================================================
# STAGE 2: RUNTIME
# Purpose: Minimal production image with only runtime dependencies
# Why: Smaller image = faster deploys, less storage, better security
# =============================================================================

FROM python:3.10-slim

# Set working directory in the runtime container
WORKDIR /app

# Install ONLY runtime dependencies (no compilers or dev tools)
# postgresql-client: Required for `psql` and PostgreSQL connections at runtime
# libpq5: PostgreSQL client library (needed by psycopg2-binary)
# curl: Used for health checks and debugging (optional, can remove)
# --no-install-recommends: Skip unnecessary packages (~150MB saved)
# && rm -rf /var/lib/apt/lists/*: Clean up apt cache immediately
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder stage
# --from=builder: Pull files from the previous build stage
# Why: Get all compiled Python packages without build tools
# Result: Final image has dependencies but not gcc, g++, etc.
COPY --from=builder /opt/venv /opt/venv

# Add virtual environment to PATH so Python finds installed packages
# Why: Makes `python` and `pip` use the venv automatically
# Alternative: Activate the venv in every RUN/CMD (verbose)
ENV PATH="/opt/venv/bin:$PATH"

# Set Python environment variables for production
# PYTHONUNBUFFERED=1: Disable output buffering
#   - Why: See logs in real-time in `fly logs`
#   - Without: Logs may be delayed by seconds/minutes
# PYTHONDONTWRITEBYTECODE=1: Don't create .pyc files
#   - Why: Saves disk space (~10MB) and slightly faster container startup
#   - Trade-off: Slightly slower first import (negligible in production)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy the entire backend application code
# .dockerignore ensures we skip __pycache__, .env, etc.
# Why: Late in Dockerfile so code changes don't invalidate dependency layers
COPY . .

# Create storage directories for user data and models
# -p: Create parent directories if needed, no error if exists
# /app/storage: User uploads and files (ephemeral on free tier)
# /app/storage/axon: Agent-specific data
# /app/storage/models: Cached ML models (sentence-transformers)
# Why: Prevents runtime errors if app tries to write before dirs exist
RUN mkdir -p /app/storage /app/storage/axon /app/storage/models

# Expose port 8000 to Fly.io's internal network
# IMPORTANT: This is documentation only, doesn't actually open ports
# Why: Tells Fly.io and developers which port the app listens on
# Actual port binding: Specified in fly.toml [http_service.internal_port]
EXPOSE 8000

# Default command: Run database migrations, then start the server
# alembic upgrade head: Apply all pending database migrations
#   - Connects to DATABASE_URL (Neon PostgreSQL)
#   - Idempotent: Safe to run multiple times
#   - Blocks until complete or fails (crashes container on failure)
# &&: Only proceed if migrations succeed
# uvicorn main:app: Start FastAPI application
#   --host 0.0.0.0: Listen on all interfaces (required for Fly.io)
#   --port ${PORT:-8000}: Use PORT env var from Fly.io, fallback to 8000
#   --proxy-headers: Trust Fly.io proxy headers (X-Forwarded-For, etc.)
#     - Why: Correct client IPs in logs, rate limiting works properly
#   --forwarded-allow-ips="*": Trust all proxies (Fly.io is the proxy)
#     - Why: Fly.io's load balancer sits in front, needs to forward headers
CMD alembic upgrade head && \
    uvicorn main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --proxy-headers \
    --forwarded-allow-ips="*"

# =============================================================================
# DOCKERFILE SUMMARY
# =============================================================================
# Final image size: ~800MB (down from ~1.2GB with single-stage build)
# Startup time: ~5-10s (migrations + FastAPI init + model loading)
# Cold start: ~15-20s (Fly.io VM boot + container start)
#
# Production optimizations:
# - Multi-stage build: Remove 400MB of build tools
# - Layer caching: Requirements layer only rebuilds when deps change
# - No .pyc files: Save 10MB disk space
# - Unbuffered output: Real-time logs
# - Migrations in CMD: Automatic schema updates on deploy
# - Proxy headers: Correct client IPs and HTTPS detection
#
# Security considerations:
# - Runs as root (Python default) - consider adding USER directive
# - No secrets in image (use Fly.io secrets)
# - Minimal attack surface (only runtime deps, no compilers)
# =============================================================================
