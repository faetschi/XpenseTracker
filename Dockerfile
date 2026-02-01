FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

EXPOSE 8501

HEALTHCHECK --interval=60s --timeout=2s --retries=3 CMD curl --fail http://localhost:8501/ || exit 1
# for dev add: "--reload"
ENTRYPOINT ["python", "app/main.py"]
