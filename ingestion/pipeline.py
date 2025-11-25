#!/usr/bin/env python3
"""
Document Ingestion Pipeline
Orchestrates the full RAG ingestion process:
1. Convert to PDF (if needed)
2. Perform OCR
3. Parse with Docling (structure-aware)
4. Generate embeddings
5. Index into Meilisearch
6. Store metadata in MongoDB
"""

import os
import logging
import requests
import tempfile
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Document processing
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Docling not available, falling back to PyPDF2")

import PyPDF2

from config import get_config
from embeddings import EmbeddingGenerator
from meilisearch_client import MeilisearchClient
from mongodb_client import MongoDBClient

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrates the complete document ingestion pipeline."""

    def __init__(self):
        """Initialize pipeline with all required clients."""
        self.config = get_config()

        # Initialize clients
        logger.info("Initializing ingestion pipeline...")
        self.embedding_gen = EmbeddingGenerator(
            model_id=self.config.embedding_model,
            provider=self.config.embedding_provider
        )
        self.meilisearch = MeilisearchClient()
        self.mongodb = MongoDBClient()

        # Initialize document converter if available
        if DOCLING_AVAILABLE:
            self.doc_converter = DocumentConverter()
        else:
            self.doc_converter = None

        logger.info("Ingestion pipeline initialized successfully")

    def process_document(self, file_path: str, user_id: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Process a document through the complete ingestion pipeline.

        Args:
            file_path: Path to document file
            user_id: ID of user who owns the document
            metadata: Optional metadata (title, tags, etc.)

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Starting document processing: {file_path}")

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Step 1: Convert to PDF if needed
                pdf_path = self._convert_to_pdf(file_path, temp_dir)
                if not pdf_path:
                    logger.error("Failed to convert document to PDF")
                    return False

                # Step 2: Perform OCR
                ocr_pdf_path = self._perform_ocr(pdf_path, temp_dir)
                if not ocr_pdf_path:
                    logger.error("Failed to perform OCR")
                    return False

                # Step 3: Parse and chunk document
                chunks = self._parse_and_chunk(ocr_pdf_path)
                if not chunks:
                    logger.error("Failed to parse document")
                    return False

                # Step 4: Generate embeddings
                chunks_with_embeddings = self._generate_embeddings(chunks)
                if not chunks_with_embeddings:
                    logger.error("Failed to generate embeddings")
                    return False

                # Step 5: Create document record in MongoDB
                doc_id = self._create_document_record(file_path, user_id, metadata)
                if not doc_id:
                    logger.error("Failed to create document record")
                    return False

                # Step 6: Format chunks for Meilisearch
                indexed_chunks = self._format_for_meilisearch(
                    chunks_with_embeddings,
                    doc_id,
                    user_id,
                    metadata
                )

                # Step 7: Index into Meilisearch
                success = self.meilisearch.index_documents(indexed_chunks)
                if not success:
                    logger.error("Failed to index documents")
                    return False

                # Step 8: Create user-document metadata
                self.mongodb.create_user_doc_meta(user_id, doc_id, metadata)

                logger.info(f"Successfully processed document: {file_path} -> {doc_id}")
                return True

        except Exception as e:
            logger.error(f"Document processing failed: {e}", exc_info=True)
            return False

    def _convert_to_pdf(self, file_path: str, temp_dir: str) -> Optional[str]:
        """
        Convert document to PDF if needed.

        Args:
            file_path: Path to source document
            temp_dir: Temporary directory for processing

        Returns:
            Path to PDF file or None on failure
        """
        file_ext = Path(file_path).suffix.lower()

        # Already a PDF
        if file_ext == '.pdf':
            logger.info("Document is already PDF, skipping conversion")
            return file_path

        # Need conversion
        logger.info(f"Converting {file_ext} to PDF...")

        try:
            with open(file_path, 'rb') as f:
                files = {'file': (Path(file_path).name, f)}
                response = requests.post(
                    self.config.converter_url,
                    files=files,
                    timeout=self.config.get('services.converter.timeout_ms', 60000) / 1000
                )

            if response.status_code == 200:
                # Save converted PDF
                pdf_path = os.path.join(temp_dir, 'converted.pdf')
                with open(pdf_path, 'wb') as f:
                    f.write(response.content)

                logger.info(f"Conversion successful: {pdf_path}")
                return pdf_path
            else:
                logger.error(f"Conversion failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Conversion error: {e}")
            return None

    def _perform_ocr(self, pdf_path: str, temp_dir: str) -> Optional[str]:
        """
        Perform OCR on PDF.

        Args:
            pdf_path: Path to PDF file
            temp_dir: Temporary directory for processing

        Returns:
            Path to OCR'd PDF or None on failure
        """
        logger.info("Performing OCR on PDF...")

        try:
            with open(pdf_path, 'rb') as f:
                files = {'file': ('document.pdf', f, 'application/pdf')}
                data = {'force_ocr': 'true'}  # Pure OCR mode

                response = requests.post(
                    self.config.ocr_url,
                    files=files,
                    data=data,
                    timeout=self.config.get('services.ocr.timeout_ms', 120000) / 1000
                )

            if response.status_code == 200:
                # Save OCR'd PDF
                ocr_pdf_path = os.path.join(temp_dir, 'ocr.pdf')
                with open(ocr_pdf_path, 'wb') as f:
                    f.write(response.content)

                logger.info(f"OCR successful: {ocr_pdf_path}")
                return ocr_pdf_path
            else:
                logger.error(f"OCR failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"OCR error: {e}")
            return None

    def _parse_and_chunk(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Parse PDF and create chunks using Docling (structure-aware) or PyPDF2 (fallback).

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of chunk dictionaries with text and metadata
        """
        logger.info("Parsing and chunking document...")

        if DOCLING_AVAILABLE and self.doc_converter:
            return self._parse_with_docling(pdf_path)
        else:
            return self._parse_with_pypdf2(pdf_path)

    def _parse_with_docling(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Parse PDF using Docling for structure-aware chunking."""
        try:
            logger.info("Using Docling for structure-aware parsing")

            # Convert document
            result = self.doc_converter.convert(pdf_path)

            chunks = []
            chunk_size = self.config.chunk_size
            chunk_overlap = self.config.chunk_overlap

            # Process each page
            for page_num, page in enumerate(result.document.pages, start=1):
                # Extract structured elements
                for element in page.elements:
                    # Get element text and type
                    text = element.text if hasattr(element, 'text') else str(element)
                    structure_type = element.label if hasattr(element, 'label') else 'paragraph'

                    # Skip empty elements
                    if not text or len(text.strip()) < 10:
                        continue

                    # Create chunk with structure metadata
                    chunk = {
                        'content_text': text.strip(),
                        'page_number': page_num,
                        'structure_type': structure_type,
                    }

                    chunks.append(chunk)

            logger.info(f"Extracted {len(chunks)} structured chunks using Docling")
            return chunks

        except Exception as e:
            logger.error(f"Docling parsing failed: {e}, falling back to PyPDF2")
            return self._parse_with_pypdf2(pdf_path)

    def _parse_with_pypdf2(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Parse PDF using PyPDF2 (fallback method)."""
        try:
            logger.info("Using PyPDF2 for basic text extraction")

            chunks = []
            chunk_size = self.config.chunk_size
            chunk_overlap = self.config.chunk_overlap

            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)

                for page_num, page in enumerate(pdf_reader.pages, start=1):
                    text = page.extract_text()

                    if not text or len(text.strip()) < 10:
                        continue

                    # Simple fixed-size chunking
                    text = text.strip()
                    for i in range(0, len(text), chunk_size - chunk_overlap):
                        chunk_text = text[i:i + chunk_size]

                        if len(chunk_text.strip()) < 50:
                            continue

                        chunk = {
                            'content_text': chunk_text.strip(),
                            'page_number': page_num,
                            'structure_type': 'paragraph',  # Default type
                        }

                        chunks.append(chunk)

            logger.info(f"Extracted {len(chunks)} chunks using PyPDF2")
            return chunks

        except Exception as e:
            logger.error(f"PyPDF2 parsing failed: {e}")
            return []

    def _generate_embeddings(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate vector embeddings for chunks.

        Args:
            chunks: List of chunk dictionaries

        Returns:
            Chunks with embeddings added
        """
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")

        try:
            # Extract texts
            texts = [chunk['content_text'] for chunk in chunks]

            # Generate embeddings
            embeddings = self.embedding_gen.embed(texts)

            # Add embeddings to chunks
            for chunk, embedding in zip(chunks, embeddings):
                chunk['_vectors'] = {'default': embedding}

            logger.info("Embeddings generated successfully")
            return chunks

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return []

    def _create_document_record(self, file_path: str, user_id: str, metadata: Dict[str, Any] = None) -> Optional[str]:
        """
        Create document record in MongoDB.

        Args:
            file_path: Original file path
            user_id: User ID
            metadata: Optional metadata

        Returns:
            Document ID or None
        """
        logger.info("Creating document record in MongoDB...")

        doc_data = {
            'owner_id': user_id,
            'title': metadata.get('title', Path(file_path).name) if metadata else Path(file_path).name,
            'filename': Path(file_path).name,
            's3_url': metadata.get('s3_url', '') if metadata else '',  # Will be set by upload handler
            'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            'file_type': Path(file_path).suffix,
        }

        return self.mongodb.create_document(doc_data)

    def _format_for_meilisearch(
        self,
        chunks: List[Dict[str, Any]],
        doc_id: str,
        user_id: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Format chunks for Meilisearch indexing.

        Args:
            chunks: List of chunks with embeddings
            doc_id: Document ID
            user_id: User ID
            metadata: Optional metadata

        Returns:
            Formatted documents for Meilisearch
        """
        logger.info("Formatting chunks for Meilisearch...")

        indexed_chunks = []
        timestamp = datetime.utcnow().isoformat()

        for idx, chunk in enumerate(chunks):
            doc = {
                'id': f"{doc_id}_chunk_{idx}",
                'document_id': doc_id,
                'user_id': user_id,
                'content_text': chunk['content_text'],
                'page_number': chunk.get('page_number', 1),
                'structure_type': chunk.get('structure_type', 'paragraph'),
                'chunk_index': idx,
                'last_modified': timestamp,
                'title': metadata.get('title', '') if metadata else '',
                'author': metadata.get('author', '') if metadata else '',
                '_vectors': chunk.get('_vectors', {}),
            }

            indexed_chunks.append(doc)

        logger.info(f"Formatted {len(indexed_chunks)} chunks for indexing")
        return indexed_chunks
