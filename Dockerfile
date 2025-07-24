FROM python:3.12-slim

# Set the OLLAMA_HOST environment variable
ENV OLLAMA_HOST=http://ollama:11434

# System packages required for unstructured document loaders
RUN apt-get update && apt-get install -y \
    build-essential \
    poppler-utils \
    libmagic1 \
    tesseract-ocr \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt --resume-retries 5

COPY . .