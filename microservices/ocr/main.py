#!/usr/bin/env python3
"""
OCR Service
Performs "Pure OCR" on PDF documents using OCRmyPDF with --force-ocr flag.
This ensures text recognition even for content-protected or scanned documents.
"""

import os
import subprocess
import tempfile
import logging
from pathlib import Path
from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = '/tmp/ocr'
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB (PDFs can be large)

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def perform_ocr(input_pdf_path, output_pdf_path, force_ocr=True):
    """
    Perform OCR on PDF using OCRmyPDF.

    Args:
        input_pdf_path: Path to input PDF
        output_pdf_path: Path for output searchable PDF
        force_ocr: If True, use --force-ocr to perform OCR even if text exists

    Returns:
        Path to OCR-processed PDF

    Raises:
        RuntimeError: If OCR processing fails
    """
    try:
        # Build OCRmyPDF command
        # --force-ocr: Perform OCR even if PDF already has text (Pure OCR mode)
        # --skip-text: Remove any existing text before OCR (ensures clean output)
        # --optimize 1: Light optimization
        # --output-type pdf: Output as standard PDF
        cmd = ['ocrmypdf']

        if force_ocr:
            # This is the critical flag for "Pure OCR" feature
            # It discards any existing text layer and performs fresh OCR
            cmd.append('--force-ocr')

        # Additional options for better results
        cmd.extend([
            '--rotate-pages',           # Auto-rotate pages based on text orientation
            '--deskew',                 # Fix skewed scans
            '--clean',                  # Clean up background noise
            '--optimize', '1',          # Light optimization
            '--output-type', 'pdf',     # Standard PDF output
            '--jobs', '2',              # Use 2 CPU cores for faster processing
        ])

        # Add input and output paths
        cmd.extend([input_pdf_path, output_pdf_path])

        logger.info(f"Processing PDF: {input_pdf_path}")
        logger.debug(f"Command: {' '.join(cmd)}")

        # Execute OCR
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout for large PDFs
        )

        # Check for errors
        if result.returncode != 0:
            # OCRmyPDF exit codes:
            # 0 = success
            # 1 = invalid arguments
            # 2 = input file error
            # 3 = missing dependency
            # 6 = already has text (shouldn't happen with --force-ocr)
            # 130 = ctrl+c
            logger.error(f"OCRmyPDF failed with code {result.returncode}: {result.stderr}")
            raise RuntimeError(f"OCR processing failed: {result.stderr}")

        # Verify output file exists
        if not os.path.exists(output_pdf_path):
            raise RuntimeError(f"Output PDF not found: {output_pdf_path}")

        logger.info(f"OCR processing successful: {output_pdf_path}")
        return output_pdf_path

    except subprocess.TimeoutExpired:
        logger.error("OCR processing timed out")
        raise RuntimeError("OCR processing timed out after 5 minutes")
    except Exception as e:
        logger.error(f"OCR error: {str(e)}")
        raise


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'ocr',
        'version': '1.0.0'
    }), 200


@app.route('/ocr', methods=['POST'])
def ocr():
    """
    Perform OCR on uploaded PDF.

    Expected request:
        - Content-Type: multipart/form-data
        - Field: file (the PDF to process)
        - Optional field: force_ocr (default: true)

    Returns:
        - Searchable PDF file (application/pdf)
        - Or error JSON with 4xx/5xx status code
    """
    # Check if file is in request
    if 'file' not in request.files:
        logger.warning("No file in request")
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    # Check if filename is empty
    if file.filename == '':
        logger.warning("Empty filename")
        return jsonify({'error': 'No file selected'}), 400

    # Validate file extension
    if not file.filename.lower().endswith('.pdf'):
        logger.warning(f"Invalid file type: {file.filename}")
        return jsonify({
            'error': 'Invalid file type',
            'message': 'Only PDF files are accepted'
        }), 400

    # Get force_ocr parameter (default to True for Pure OCR mode)
    force_ocr = request.form.get('force_ocr', 'true').lower() == 'true'

    # Create temporary directory for this OCR job
    with tempfile.TemporaryDirectory(dir=UPLOAD_FOLDER) as temp_dir:
        try:
            # Save uploaded file
            filename = secure_filename(file.filename)
            input_path = os.path.join(temp_dir, f"input_{filename}")
            file.save(input_path)

            # Check file size
            file_size = os.path.getsize(input_path)
            if file_size > MAX_FILE_SIZE:
                logger.warning(f"File too large: {file_size} bytes")
                return jsonify({
                    'error': 'File too large',
                    'max_size_mb': MAX_FILE_SIZE / (1024 * 1024)
                }), 400

            logger.info(f"Processing PDF: {filename} ({file_size} bytes, force_ocr={force_ocr})")

            # Define output path
            output_path = os.path.join(temp_dir, f"output_{filename}")

            # Perform OCR
            ocr_pdf_path = perform_ocr(input_path, output_path, force_ocr=force_ocr)

            # Send OCR-processed PDF file
            return send_file(
                ocr_pdf_path,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f"ocr_{filename}"
            )

        except RuntimeError as e:
            logger.error(f"OCR processing failed: {str(e)}")
            return jsonify({'error': str(e)}), 500
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500


@app.route('/', methods=['GET'])
def index():
    """Service information endpoint."""
    return jsonify({
        'service': 'OCR Service',
        'version': '1.0.0',
        'description': 'Pure OCR processing for PDF documents using OCRmyPDF',
        'endpoints': {
            'POST /ocr': 'Perform OCR on PDF (with --force-ocr by default)',
            'GET /health': 'Health check'
        },
        'features': [
            'Pure OCR mode (--force-ocr)',
            'Auto-rotation',
            'Deskewing',
            'Background noise cleaning',
            'Multi-core processing'
        ],
        'max_file_size_mb': MAX_FILE_SIZE / (1024 * 1024)
    }), 200


if __name__ == '__main__':
    logger.info("Starting OCR Service on port 3000")
    app.run(host='0.0.0.0', port=3000, debug=False)
