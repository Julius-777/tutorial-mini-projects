# OCR Service

A specialized microservice for "Pure OCR" processing of PDF documents using OCRmyPDF. This service performs text recognition even on content-protected or scanned documents.

## Features

- **Pure OCR Mode**: Uses `--force-ocr` flag to perform OCR even if text already exists
- **Auto-rotation**: Automatically rotates pages based on text orientation
- **Deskewing**: Corrects skewed scans
- **Background cleaning**: Removes background noise from scanned documents
- **Multi-core processing**: Utilizes multiple CPU cores for faster processing
- **REST API**: Simple POST endpoint for easy integration
- **Health monitoring**: Built-in health check endpoint

## The "Pure OCR" Feature

The `--force-ocr` flag is critical for handling:
- Content-protected PDFs with broken or hidden text layers
- Scanned documents that appear to have text but are actually images
- PDFs with poor-quality OCR that needs to be redone
- Mixed documents with both text and scanned pages

This ensures all content is searchable and extractable, regardless of the original PDF structure.

## API Endpoints

### POST /ocr

Perform OCR on a PDF document.

**Request:**
- Content-Type: `multipart/form-data`
- Field: `file` (the PDF to process)
- Optional field: `force_ocr` (default: `true`)

**Response:**
- Success: Searchable PDF file (`application/pdf`)
- Error: JSON with error message and appropriate status code

**Example:**
```bash
# Basic usage (with force OCR)
curl -X POST -F "file=@scanned.pdf" http://localhost:3002/ocr --output searchable.pdf

# With explicit force_ocr parameter
curl -X POST -F "file=@document.pdf" -F "force_ocr=true" http://localhost:3002/ocr --output searchable.pdf

# Without force OCR (only OCR pages without text)
curl -X POST -F "file=@document.pdf" -F "force_ocr=false" http://localhost:3002/ocr --output searchable.pdf
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "ocr",
  "version": "1.0.0"
}
```

### GET /

Service information.

**Response:**
```json
{
  "service": "OCR Service",
  "version": "1.0.0",
  "description": "Pure OCR processing for PDF documents using OCRmyPDF",
  "endpoints": {...},
  "features": [...],
  "max_file_size_mb": 200
}
```

## Configuration

- **Port**: 3000 (mapped to 3002 on host in docker-compose)
- **Max File Size**: 200 MB
- **Processing Timeout**: 5 minutes (300 seconds)
- **CPU Cores Used**: 2 (configurable)

## OCRmyPDF Options Explained

The service uses these OCRmyPDF flags:

- `--force-ocr`: **Pure OCR mode** - Discard existing text and perform fresh OCR
- `--rotate-pages`: Auto-detect and correct page orientation
- `--deskew`: Straighten pages that are slightly rotated
- `--clean`: Remove background noise and artifacts
- `--optimize 1`: Apply light compression to output
- `--output-type pdf`: Generate standard PDF format
- `--jobs 2`: Use 2 CPU cores for parallel processing

## Building and Running

### With Docker Compose (Recommended)
```bash
docker-compose up ocr
```

### Standalone Docker
```bash
cd microservices/ocr
docker build -t ocr-service .
docker run -p 3002:3000 ocr-service
```

### Local Development
```bash
# Install OCRmyPDF and Tesseract first
# On Ubuntu/Debian:
sudo apt-get install ocrmypdf tesseract-ocr

# On macOS:
brew install ocrmypdf

# Install Python dependencies
pip install -r requirements.txt

# Run the service
python main.py
```

## Error Handling

The service returns appropriate HTTP status codes:
- **200**: Successful OCR processing
- **400**: Bad request (no file, invalid type, file too large)
- **500**: Server error (OCR failed, timeout, processing error)

## OCRmyPDF Exit Codes

The underlying OCRmyPDF tool uses these exit codes:
- **0**: Success
- **1**: Invalid arguments
- **2**: Input file error
- **3**: Missing dependency (e.g., Tesseract)
- **6**: Already has text (won't occur with `--force-ocr`)
- **130**: Interrupted (Ctrl+C)

## Architecture Notes

This service implements the OCR microservice pattern from Section 4.2 of the Cognitive Search architecture document. It uses OCRmyPDF's `--force-ocr` flag to replicate the "Pure OCR" feature from the original PDF Search application, ensuring text recognition works even for content-protected documents.

## Performance Considerations

- Large PDFs (>50 pages) may take several minutes to process
- Scanned images at high DPI will take longer but produce better results
- The service processes 2 pages in parallel by default (configurable via `--jobs`)
- Temporary files are automatically cleaned up after each request
