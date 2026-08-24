FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy all application files and install project CLI entrypoints
COPY . .
RUN pip install --no-cache-dir -e .

EXPOSE 8000
EXPOSE 8080

# Default MCP entrypoint: standard stdio JSON-RPC for Glama / Claude / Cursor, or HTTP if specified
CMD ["python", "main.py"]
