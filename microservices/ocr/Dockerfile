# Dockerfile for OCR Service
# Uses OCRmyPDF for "Pure OCR" processing of PDF documents

FROM jbarlow83/ocrmypdf:latest

# Switch to root to install additional packages
USER root

# Install Python Flask and dependencies
RUN pip install --no-cache-dir \
    Flask==3.0.0 \
    Werkzeug==3.0.1 \
    requests==2.31.0

# Create app directory
WORKDIR /app

# Copy application code
COPY main.py .
COPY requirements.txt .

# Create temporary directory for file processing
RUN mkdir -p /tmp/ocr && chmod 777 /tmp/ocr

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:3000/health')"

# Run the Flask application
CMD ["python3", "main.py"]
