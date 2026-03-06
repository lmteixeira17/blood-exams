# =============================================================================
# Blood Lab - Multi-stage Dockerfile
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies (including poppler for pdf2image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Collect static files (use dummy key for build only)
RUN SECRET_KEY='build-only-dummy-key-not-used-in-production' \
    DEBUG=True \
    python manage.py collectstatic --noinput

# -----------------------------------------------------------------------------
# Stage 2: Runtime
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --from=builder /app/core /app/core
COPY --from=builder /app/blood_exams /app/blood_exams
COPY --from=builder /app/staticfiles /app/staticfiles
COPY --from=builder /app/static /app/static
COPY --from=builder /app/manage.py /app/manage.py
COPY --from=builder /app/entrypoint.sh /app/entrypoint.sh

# Create media directory
RUN mkdir -p /app/media/exams /app/logs

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Entrypoint: migrate + configure site + start gunicorn
CMD ["sh", "/app/entrypoint.sh"]
