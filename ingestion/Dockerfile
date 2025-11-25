# Dockerfile for Ingestion Service
# Asynchronous RAG pipeline orchestrator using Python, LangChain, and Docling

FROM python:3.11-slim

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies for document processing
RUN apt-get update && apt-get install -y \
    build-essential \
    libpoppler-dev \
    libpoppler-cpp-dev \
    poppler-utils \
    tesseract-ocr \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for document processing
RUN mkdir -p /app/documents /app/temp && chmod 777 /app/documents /app/temp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the ingestion worker
CMD ["python", "main.py"]
