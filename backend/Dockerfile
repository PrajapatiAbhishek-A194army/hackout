# ==============================================================================
# AI-Powered Renewable Generation Forecasting Platform - Backend Dockerfile
# Multi-stage production container with security hardening & model artifact caching
# ==============================================================================

FROM python:3.10-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies to a clean prefix
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Final runtime image
FROM python:3.10-slim AS runner

WORKDIR /app

# Install runtime library dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1001 appuser

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source code and configurations
COPY alembic.ini ./
COPY app ./app
COPY trained_models ./trained_models
COPY datasets ./datasets
COPY reports_archive ./reports_archive

# Ensure runtime directories exist and have correct permissions
RUN mkdir -p /app/reports_archive /app/trained_models \
    && chown -R appuser:appuser /app

USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
