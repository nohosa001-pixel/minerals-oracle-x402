FROM python:3.11-slim

# Install Astral uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Configure virtual environment and universal PATH
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtualenv and install dependencies using uv (both in venv and system)
COPY requirements.txt .
COPY pyproject.toml .
RUN uv venv /app/.venv && \
    uv pip install --no-cache -r requirements.txt && \
    uv pip install --system --no-cache -r requirements.txt

# Copy all application files and install project
COPY . .
RUN uv pip install --no-cache -e . && \
    uv pip install --system --no-cache -e .

# Symlink all binaries across all system search paths for 100% execution guarantee
RUN ln -sf /app/.venv/bin/uvicorn /usr/local/bin/uvicorn && \
    ln -sf /app/.venv/bin/uvicorn /usr/bin/uvicorn && \
    ln -sf /app/.venv/bin/uvicorn /bin/uvicorn && \
    ln -sf /app/.venv/bin/python /usr/local/bin/python && \
    ln -sf /app/.venv/bin/python /usr/bin/python && \
    ln -sf /app/.venv/bin/python3 /usr/bin/python3 && \
    ln -sf /app/.venv/bin/python /bin/python && \
    ln -sf /app/.venv/bin/python3 /bin/python3 && \
    chmod -R 755 /app /app/.venv /usr/local/bin /usr/bin /bin

EXPOSE 8000
EXPOSE 8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
