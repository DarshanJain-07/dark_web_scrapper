# Multi-stage build for Dark Web Scraper API
FROM python:3.12-slim as builder

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Set working directory
WORKDIR /app

# Copy dependency files and README
COPY pyproject.toml uv.lock README.md ./

# Install dependencies
RUN uv sync --frozen --no-cache

# Production stage
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY api/ ./api/
COPY pyproject.toml uv.lock README.md ./

# Create non-root user for security
RUN groupadd -r apiuser && useradd -r -g apiuser apiuser
RUN chown -R apiuser:apiuser /app
USER apiuser

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Expose port
EXPOSE 8000

# Health check using Python
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the API
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
