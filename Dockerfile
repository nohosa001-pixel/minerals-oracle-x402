FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Ensure python symlinks exist everywhere before pip installs
RUN ln -sf $(which python3) /usr/local/bin/python && \
    ln -sf $(which python3) /usr/bin/python && \
    ln -sf $(which python3) /usr/bin/python3 && \
    ln -sf $(which python3) /bin/python && \
    ln -sf $(which python3) /bin/python3

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Ensure uvicorn binary has universal shebang and symlinks in all bin directories
RUN sed -i '1s|^.*$|#!/usr/bin/env python3|' /usr/local/bin/uvicorn && \
    chmod 755 /usr/local/bin/uvicorn && \
    ln -sf /usr/local/bin/uvicorn /usr/bin/uvicorn && \
    ln -sf /usr/local/bin/uvicorn /bin/uvicorn

# Copy all application files and install package
COPY . .
RUN pip install --no-cache-dir -e .

RUN chmod -R 755 /app /usr/local/bin /usr/bin /bin

EXPOSE 8000
EXPOSE 8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
