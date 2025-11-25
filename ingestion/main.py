#!/usr/bin/env python3
"""
Ingestion Service - Main Entry Point
Orchestrates the RAG ingestion pipeline for document processing.

This service can run in two modes:
1. Worker mode: Continuously polls SQS queue for jobs (production)
2. CLI mode: Process documents from command line (development/testing)
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path

from config import get_config
from pipeline import IngestionPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class IngestionWorker:
    """Worker for processing document ingestion jobs."""

    def __init__(self):
        """Initialize ingestion worker."""
        self.config = get_config()
        self.pipeline = IngestionPipeline()
        self.running = True

        logger.info("Ingestion worker initialized")

    def process_local_documents(self, documents_dir: str = "/app/documents"):
        """
        Process documents from local directory (for testing).

        Args:
            documents_dir: Directory containing documents to process
        """
        logger.info(f"Scanning for documents in: {documents_dir}")

        if not os.path.exists(documents_dir):
            logger.warning(f"Documents directory not found: {documents_dir}")
            return

        # Get list of documents
        documents = []
        for ext in ['*.pdf', '*.docx', '*.pptx', '*.doc', '*.ppt']:
            documents.extend(Path(documents_dir).glob(ext))

        if not documents:
            logger.info("No documents found to process")
            return

        logger.info(f"Found {len(documents)} documents to process")

        # Process each document
        for doc_path in documents:
            try:
                logger.info(f"Processing: {doc_path.name}")

                # Use test user ID for local processing
                user_id = "test_user_001"
                metadata = {
                    'title': doc_path.stem,
                    'tags': ['imported'],
                }

                success = self.pipeline.process_document(
                    str(doc_path),
                    user_id,
                    metadata
                )

                if success:
                    logger.info(f"✓ Successfully processed: {doc_path.name}")
                else:
                    logger.error(f"✗ Failed to process: {doc_path.name}")

            except Exception as e:
                logger.error(f"Error processing {doc_path.name}: {e}", exc_info=True)

        logger.info("Finished processing all documents")

    def run_worker(self, poll_interval: int = 10):
        """
        Run as continuous worker (for SQS integration in production).

        Args:
            poll_interval: Seconds between queue polls
        """
        logger.info("Starting ingestion worker in continuous mode...")
        logger.info(f"Poll interval: {poll_interval} seconds")

        try:
            while self.running:
                try:
                    # TODO: In production, poll SQS queue for jobs
                    # For now, just process local documents once
                    self.process_local_documents()

                    # Sleep before next poll
                    logger.info(f"Waiting {poll_interval} seconds before next check...")
                    time.sleep(poll_interval)

                except KeyboardInterrupt:
                    logger.info("Received interrupt signal, shutting down...")
                    self.running = False
                    break

                except Exception as e:
                    logger.error(f"Worker error: {e}", exc_info=True)
                    time.sleep(poll_interval)

        finally:
            logger.info("Ingestion worker stopped")

    def process_single_document(self, file_path: str, user_id: str = "test_user"):
        """
        Process a single document (for CLI mode).

        Args:
            file_path: Path to document
            user_id: User ID (defaults to test_user)
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False

        logger.info(f"Processing single document: {file_path}")

        metadata = {
            'title': Path(file_path).stem,
            'tags': ['cli-import'],
        }

        success = self.pipeline.process_document(file_path, user_id, metadata)

        if success:
            logger.info(f"✓ Successfully processed: {file_path}")
        else:
            logger.error(f"✗ Failed to process: {file_path}")

        return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Cognitive Search Ingestion Service',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run as continuous worker
  python main.py --mode worker

  # Process documents from directory
  python main.py --mode batch --dir /app/documents

  # Process single document
  python main.py --mode single --file /path/to/document.pdf --user user123
        """
    )

    parser.add_argument(
        '--mode',
        choices=['worker', 'batch', 'single'],
        default='worker',
        help='Execution mode: worker (continuous), batch (process directory), single (one file)'
    )

    parser.add_argument(
        '--dir',
        default='/app/documents',
        help='Directory containing documents to process (for batch mode)'
    )

    parser.add_argument(
        '--file',
        help='Path to single document to process (for single mode)'
    )

    parser.add_argument(
        '--user',
        default='test_user',
        help='User ID for document ownership'
    )

    parser.add_argument(
        '--poll-interval',
        type=int,
        default=10,
        help='Seconds between queue polls in worker mode'
    )

    args = parser.parse_args()

    # Banner
    logger.info("=" * 80)
    logger.info("Cognitive Search - Ingestion Service")
    logger.info("RAG Pipeline Orchestrator")
    logger.info("=" * 80)

    try:
        worker = IngestionWorker()

        if args.mode == 'worker':
            # Continuous worker mode
            worker.run_worker(poll_interval=args.poll_interval)

        elif args.mode == 'batch':
            # Batch process directory
            worker.process_local_documents(args.dir)

        elif args.mode == 'single':
            # Process single document
            if not args.file:
                logger.error("--file is required for single mode")
                sys.exit(1)

            success = worker.process_single_document(args.file, args.user)
            sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
