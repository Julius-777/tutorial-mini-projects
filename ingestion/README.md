# Ingestion Service

The RAG (Retrieval-Augmented Generation) pipeline orchestrator for Cognitive Search. This service is the "factory brain" that processes documents through the complete ingestion workflow.

## Architecture

This service implements the asynchronous ingestion pipeline from **Section 4.3** of the architecture document. It orchestrates multiple specialized services and libraries to create a high-fidelity, structure-aware document index.

## Pipeline Workflow

The ingestion pipeline executes these steps sequentially:

### 1. **Document Conversion** (if needed)
- Checks if document is already PDF
- If not, calls the `converter` microservice
- Converts Office/iWork documents to PDF using LibreOffice

### 2. **OCR Processing**
- Calls the `ocr` microservice
- Performs "Pure OCR" using OCRmyPDF with `--force-ocr` flag
- Ensures text layer is clean and searchable

### 3. **Parsing & Chunking**
- **Primary method**: Docling for structure-aware parsing
  - Identifies headers, tables, paragraphs
  - Preserves document structure
  - Enables "keyword placement" boosting
- **Fallback method**: PyPDF2 for basic text extraction
- Respects chunk size and overlap from config.yaml

### 4. **Embedding Generation**
- **Local mode**: Uses sentence-transformers (default: all-MiniLM-L6-v2)
- **Bedrock mode**: Uses AWS Bedrock Titan Embeddings
- Generates vector embeddings for each chunk
- Configurable batch processing

### 5. **Meilisearch Indexing**
- Formats chunks with metadata (page, structure type, etc.)
- Performs bulk write to Meilisearch
- Includes both text and vector embeddings
- Enables hybrid search (lexical + semantic)

### 6. **MongoDB Metadata Storage**
- Creates document record with ownership info
- Creates user-document relationship
- Stores tags and folder metadata
- Enables annotation and bookmark features

## Components

### Core Modules

- **`main.py`** - Entry point and worker orchestration
- **`pipeline.py`** - Complete ingestion workflow orchestrator
- **`config.py`** - Configuration loader (reads config.yaml and env vars)
- **`embeddings.py`** - Embedding generation (local or Bedrock)
- **`meilisearch_client.py`** - Meilisearch indexing client
- **`mongodb_client.py`** - MongoDB metadata storage client

## Running the Service

### With Docker Compose (Recommended)

```bash
# Start all services including ingestion
docker-compose up

# Start only ingestion service
docker-compose up ingestion

# Run in batch mode (process all documents once)
docker-compose run ingestion python main.py --mode batch --dir /app/documents

# Process single document
docker-compose run ingestion python main.py --mode single --file /app/documents/test.pdf --user user123
```

### Standalone Docker

```bash
cd ingestion
docker build -t ingestion-service .
docker run -v $(pwd)/config.yaml:/app/config.yaml -v ./documents:/app/documents ingestion-service
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export CONFIG_PATH=../config.yaml
export MEILI_HOST=http://localhost:7700
export MEILI_MASTER_KEY=your_key
export MONGO_CONNECTION_STRING=mongodb://localhost:27017/pdf-search-app

# Run worker mode (continuous)
python main.py --mode worker

# Run batch mode (process directory once)
python main.py --mode batch --dir ../local-documents

# Process single file
python main.py --mode single --file ../test.pdf --user testuser
```

## Execution Modes

### 1. Worker Mode (Continuous)
```bash
python main.py --mode worker --poll-interval 10
```
- Runs continuously
- Polls for new documents every N seconds
- **Production mode** (will integrate with SQS)

### 2. Batch Mode
```bash
python main.py --mode batch --dir /path/to/documents
```
- Processes all documents in a directory
- Runs once then exits
- Good for bulk imports

### 3. Single Mode
```bash
python main.py --mode single --file /path/to/doc.pdf --user user123
```
- Processes one specific document
- Good for testing and CLI usage

## Configuration

The service reads configuration from two sources:

### 1. config.yaml (Application Settings)
```yaml
rag:
  embedding:
    model_id: "sentence-transformers/all-MiniLM-L6-v2"
    provider: "local"  # or "bedrock"
  chunking:
    strategy: "hierarchical"
    chunk_size: 1000
    chunk_overlap: 200
services:
  meilisearch:
    host: "http://meilisearch:7700"
    index_name: "document-index"
  converter:
    url: "http://converter:3000"
  ocr:
    url: "http://ocr:3000"
```

### 2. Environment Variables (Secrets)
```bash
MEILI_MASTER_KEY=your_key
MONGO_CONNECTION_STRING=mongodb://mongo:27017/pdf-search-app
BEDROCK_ACCESS_KEY=your_aws_key
BEDROCK_SECRET_KEY=your_aws_secret
```

## Dependencies

### Document Processing
- **Docling** - Structure-aware PDF parsing (primary)
- **PyPDF2** - Basic PDF text extraction (fallback)
- **pdfplumber** - Advanced PDF analysis

### AI/ML
- **sentence-transformers** - Local embedding generation
- **torch** - Required by sentence-transformers
- **boto3** - AWS Bedrock integration

### Search & Storage
- **meilisearch** - Python client for Meilisearch
- **pymongo** - MongoDB client

### LangChain
- **langchain** - RAG framework
- **langchain-community** - Community integrations

### HTTP & Config
- **requests** - HTTP client for microservices
- **pyyaml** - YAML configuration parsing

## Supported File Types

The pipeline automatically handles:

- **PDF** - Direct processing
- **Microsoft Office** - .doc, .docx, .ppt, .pptx, .xls, .xlsx
- **Apple iWork** - .pages, .keynote, .numbers
- **OpenDocument** - .odt, .odp, .ods
- **Rich Text** - .rtf

## Performance Considerations

### Memory Usage
- Docling and sentence-transformers are memory-intensive
- Recommended: 2GB+ RAM per worker
- Large PDFs (>100 pages) may require 4GB+

### Processing Time
- Conversion: 5-30 seconds per document
- OCR: 30-120 seconds per document (depends on page count)
- Parsing: 10-60 seconds
- Embedding: 1-5 seconds per batch
- **Total**: 1-5 minutes per document

### Scaling
- Each worker processes one document at a time
- Scale horizontally by running multiple containers
- Use SQS queue for work distribution (production)

## Error Handling

The pipeline includes comprehensive error handling:

- **Conversion failures**: Logged and skipped
- **OCR timeouts**: 5-minute limit with proper cleanup
- **Parse errors**: Falls back to PyPDF2
- **Embedding failures**: Logged with context
- **Index failures**: Rolled back with cleanup

All errors are logged with full context for debugging.

## Monitoring

### Health Checks
The Docker container includes a health check that verifies:
- Python runtime is working
- Dependencies are loaded

### Logging
All operations are logged with:
- Timestamp
- Module name
- Log level
- Message
- Stack trace (for errors)

Example:
```
2024-01-15 10:30:45 - pipeline - INFO - Starting document processing: test.pdf
2024-01-15 10:30:50 - pipeline - INFO - Conversion successful: /tmp/xyz/converted.pdf
2024-01-15 10:31:20 - pipeline - INFO - OCR successful: /tmp/xyz/ocr.pdf
2024-01-15 10:31:35 - pipeline - INFO - Extracted 45 structured chunks using Docling
```

## Testing

### Test with Sample Documents
```bash
# Create test documents directory
mkdir -p local-documents

# Copy test files
cp test.pdf local-documents/

# Run ingestion
docker-compose run ingestion python main.py --mode batch --dir /app/documents
```

### Verify Results

**Check Meilisearch:**
```bash
curl http://localhost:7700/indexes/document-index/stats \
  -H "Authorization: Bearer your_master_key"
```

**Check MongoDB:**
```bash
docker-compose exec mongo mongosh pdf-search-app --eval "db.documents.find().pretty()"
```

## Integration with API Service

The ingestion service is designed to be called asynchronously:

1. User uploads file via API
2. API stores file in S3
3. API sends message to SQS queue
4. Ingestion worker picks up message
5. Worker processes document through pipeline
6. User can search document immediately after indexing

## Future Enhancements

- [ ] SQS integration for production job queue
- [ ] Progress tracking and status updates
- [ ] Document update/reprocessing
- [ ] Incremental indexing
- [ ] Advanced chunking strategies
- [ ] Multi-modal support (images, tables)
- [ ] Re-ranking model integration

## Troubleshooting

### "Docling not available" Warning
- Docling may fail to install on some platforms
- Service automatically falls back to PyPDF2
- For full functionality, ensure compatible Python/OS

### Converter Service Timeout
- Increase timeout in config.yaml
- Check LibreOffice installation in converter service
- Verify file is not corrupted

### OCR Service Timeout
- Large PDFs take time (5+ minutes for 100+ pages)
- Increase timeout or split large documents
- Check OCRmyPDF logs in container

### Embedding Generation Fails
- Local mode: Ensure sentence-transformers is installed
- Bedrock mode: Verify AWS credentials
- Check model ID is correct

### Meilisearch Indexing Fails
- Verify Meilisearch is running
- Check master key is correct
- Ensure index settings are valid
- Check disk space on Meilisearch volume

## Architecture Alignment

This service implements:
- **Section 4.3**: RAG Ingestion Orchestrator
- **Section 3.2**: Meilisearch index configuration
- **Section 6.2**: MongoDB metadata storage
- **Table 2**: Feature mapping (structure-aware chunking enables attribute ranking)
