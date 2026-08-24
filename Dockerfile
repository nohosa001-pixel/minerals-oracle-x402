# Stage 1: Build & Dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# Stage 2: Final Ultra-Lightweight Production Runtime
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/root/.local/bin:$PATH \
    PORT=8000 \
    HOST=0.0.0.0

# Copy installed python wheels from builder
COPY --from=builder /root/.local /root/.local

# Copy application files
COPY app/ ./app/
COPY .well-known/ ./.well-known/
COPY mcp_tool_spec.json ./mcp_tool_spec.json
COPY README.md ./README.md

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
