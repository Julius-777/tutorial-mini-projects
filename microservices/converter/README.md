# Document Converter Service

A lightweight microservice that converts Office and iWork documents to PDF using LibreOffice headless mode.

## Features

- Convert Microsoft Office files (Word, PowerPoint, Excel)
- Convert Apple iWork files (Pages, Keynote, Numbers)
- Convert OpenDocument formats
- Convert RTF files
- REST API with simple POST endpoint
- Health check endpoint
- Automatic cleanup of temporary files

## Supported Formats

- **Microsoft Office**: .doc, .docx, .ppt, .pptx, .xls, .xlsx, .rtf
- **Apple iWork**: .pages, .keynote, .numbers
- **OpenDocument**: .odt, .odp, .ods

## API Endpoints

### POST /convert

Convert a document to PDF.

**Request:**
- Content-Type: `multipart/form-data`
- Field: `file` (the document to convert)

**Response:**
- Success: PDF file (`application/pdf`)
- Error: JSON with error message and appropriate status code

**Example:**
```bash
curl -X POST -F "file=@document.docx" http://localhost:3001/convert --output result.pdf
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "converter",
  "version": "1.0.0"
}
```

### GET /

Service information.

**Response:**
```json
{
  "service": "Document Converter Service",
  "version": "1.0.0",
  "endpoints": {...},
  "supported_formats": [...],
  "max_file_size_mb": 100
}
```

## Configuration

- **Port**: 3000 (mapped to 3001 on host in docker-compose)
- **Max File Size**: 100 MB
- **Conversion Timeout**: 60 seconds

## Building and Running

### With Docker Compose (Recommended)
```bash
docker-compose up converter
```

### Standalone Docker
```bash
cd microservices/converter
docker build -t converter-service .
docker run -p 3001:3000 converter-service
```

### Local Development
```bash
# Install LibreOffice first
sudo apt-get install libreoffice

# Install Python dependencies
pip install -r requirements.txt

# Run the service
python main.py
```

## Error Handling

The service returns appropriate HTTP status codes:
- **200**: Successful conversion
- **400**: Bad request (no file, invalid type, file too large)
- **500**: Server error (conversion failed, timeout)

## Architecture Notes

This service implements the converter microservice pattern from Section 4.1 of the Cognitive Search architecture document. It uses LibreOffice's headless mode for server-side document conversion, providing a robust solution for handling multiple office document formats.
