FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    PATH="/usr/local/bin:/usr/bin:$PATH"

# Install build dependencies and clean up
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies globally
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create symlinks in /usr/bin to guarantee execution regardless of PATH overrides
RUN ln -sf /usr/local/bin/uvicorn /usr/bin/uvicorn && \
    ln -sf /usr/local/bin/python /usr/bin/python && \
    ln -sf /usr/local/bin/python3 /usr/bin/python3

# Copy application files
COPY app/ ./app/
COPY .well-known/ ./.well-known/
COPY mcp_tool_spec.json ./mcp_tool_spec.json
COPY glama.json ./glama.json
COPY llms.txt ./llms.txt
COPY README.md ./README.md

EXPOSE 8000
EXPOSE 8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
