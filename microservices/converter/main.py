#!/usr/bin/env python3
"""
Document Converter Service
Converts Office (Word, PowerPoint) and iWork (Pages, Keynote) files to PDF using LibreOffice.
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
UPLOAD_FOLDER = '/tmp/converter'
ALLOWED_EXTENSIONS = {
    # Microsoft Office
    'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'rtf',
    # Apple iWork
    'pages', 'keynote', 'numbers',
    # OpenDocument
    'odt', 'odp', 'ods'
}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def convert_to_pdf(input_path, output_dir):
    """
    Convert document to PDF using LibreOffice headless mode.

    Args:
        input_path: Path to input document
        output_dir: Directory for output PDF

    Returns:
        Path to converted PDF file

    Raises:
        RuntimeError: If conversion fails
    """
    try:
        # Build LibreOffice command
        # --headless: Run without GUI
        # --convert-to pdf: Convert to PDF format
        # --outdir: Output directory
        cmd = [
            'libreoffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', output_dir,
            input_path
        ]

        logger.info(f"Converting file: {input_path}")
        logger.debug(f"Command: {' '.join(cmd)}")

        # Execute conversion
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )

        # Check for errors
        if result.returncode != 0:
            logger.error(f"LibreOffice conversion failed: {result.stderr}")
            raise RuntimeError(f"Conversion failed: {result.stderr}")

        # Find the output PDF file
        # LibreOffice creates PDF with same name but .pdf extension
        input_filename = Path(input_path).stem
        output_pdf = Path(output_dir) / f"{input_filename}.pdf"

        if not output_pdf.exists():
            raise RuntimeError(f"Output PDF not found: {output_pdf}")

        logger.info(f"Conversion successful: {output_pdf}")
        return str(output_pdf)

    except subprocess.TimeoutExpired:
        logger.error("Conversion timed out")
        raise RuntimeError("Conversion timed out after 60 seconds")
    except Exception as e:
        logger.error(f"Conversion error: {str(e)}")
        raise


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'converter',
        'version': '1.0.0'
    }), 200


@app.route('/convert', methods=['POST'])
def convert():
    """
    Convert uploaded document to PDF.

    Expected request:
        - Content-Type: multipart/form-data
        - Field: file (the document to convert)

    Returns:
        - PDF file (application/pdf)
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
    if not allowed_file(file.filename):
        logger.warning(f"Invalid file type: {file.filename}")
        return jsonify({
            'error': 'Invalid file type',
            'allowed_types': list(ALLOWED_EXTENSIONS)
        }), 400

    # Create temporary directory for this conversion
    with tempfile.TemporaryDirectory(dir=UPLOAD_FOLDER) as temp_dir:
        try:
            # Save uploaded file
            filename = secure_filename(file.filename)
            input_path = os.path.join(temp_dir, filename)
            file.save(input_path)

            # Check file size
            file_size = os.path.getsize(input_path)
            if file_size > MAX_FILE_SIZE:
                logger.warning(f"File too large: {file_size} bytes")
                return jsonify({
                    'error': 'File too large',
                    'max_size_mb': MAX_FILE_SIZE / (1024 * 1024)
                }), 400

            logger.info(f"Processing file: {filename} ({file_size} bytes)")

            # Convert to PDF
            output_pdf_path = convert_to_pdf(input_path, temp_dir)

            # Send PDF file
            return send_file(
                output_pdf_path,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f"{Path(filename).stem}.pdf"
            )

        except RuntimeError as e:
            logger.error(f"Conversion failed: {str(e)}")
            return jsonify({'error': str(e)}), 500
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500


@app.route('/', methods=['GET'])
def index():
    """Service information endpoint."""
    return jsonify({
        'service': 'Document Converter Service',
        'version': '1.0.0',
        'endpoints': {
            'POST /convert': 'Convert document to PDF',
            'GET /health': 'Health check'
        },
        'supported_formats': list(ALLOWED_EXTENSIONS),
        'max_file_size_mb': MAX_FILE_SIZE / (1024 * 1024)
    }), 200


if __name__ == '__main__':
    logger.info("Starting Document Converter Service on port 3000")
    app.run(host='0.0.0.0', port=3000, debug=False)
