#!/usr/bin/env python3
"""
Meilisearch client for document indexing
Implements hybrid search with text and vectors
"""

import logging
from typing import List, Dict, Any
import meilisearch
from config import get_config

logger = logging.getLogger(__name__)


class MeilisearchClient:
    """Client for indexing documents into Meilisearch."""

    def __init__(self):
        """Initialize Meilisearch client."""
        config = get_config()
        self.host = config.meilisearch_host
        self.key = config.meilisearch_key
        self.index_name = config.meilisearch_index

        logger.info(f"Connecting to Meilisearch at {self.host}")

        try:
            self.client = meilisearch.Client(self.host, self.key)
            # Test connection
            self.client.health()
            logger.info("Meilisearch connection successful")

            # Get or create index
            self.index = self._setup_index()

        except Exception as e:
            logger.error(f"Failed to connect to Meilisearch: {e}")
            raise

    def _setup_index(self):
        """Create or update index with proper settings."""
        try:
            # Try to get existing index
            index = self.client.index(self.index_name)
            logger.info(f"Using existing index: {self.index_name}")

        except Exception:
            # Create new index
            logger.info(f"Creating new index: {self.index_name}")
            task = self.client.create_index(self.index_name, {'primaryKey': 'id'})
            self.client.wait_for_task(task.task_uid)
            index = self.client.index(self.index_name)

        # Configure index settings (from Section 3.2 of architecture document)
        self._configure_index_settings(index)

        return index

    def _configure_index_settings(self, index):
        """
        Configure index settings for optimal search performance.
        These settings implement the requirements from Table 2 of the architecture document.
        """
        config = get_config()

        # Get settings from config or use defaults
        settings = config.get('services.meilisearch.settings', {})

        # Default settings if not in config
        default_settings = {
            'searchableAttributes': [
                'title',
                'content_text',
                'author'
            ],
            'filterableAttributes': [
                'document_id',
                'user_id',
                'last_modified',
                'structure_type',
                'page_number'
            ],
            'sortableAttributes': [
                'last_modified'
            ],
            'rankingRules': [
                'words',
                'typo',
                'proximity',
                'attribute',
                'sort',
                'exactness'
            ],
            'displayedAttributes': [
                '*'
            ],
            'typoTolerance': {
                'enabled': True,
                'minWordSizeForTypos': {
                    'oneTypo': 5,
                    'twoTypos': 9
                }
            }
        }

        # Merge with config settings
        final_settings = {**default_settings, **settings}

        try:
            logger.info("Configuring index settings...")
            task = index.update_settings(final_settings)
            self.client.wait_for_task(task.task_uid)
            logger.info("Index settings configured successfully")
        except Exception as e:
            logger.warning(f"Failed to update index settings: {e}")

    def index_documents(self, documents: List[Dict[str, Any]], batch_size: int = 100) -> bool:
        """
        Index documents into Meilisearch.

        Args:
            documents: List of document dictionaries to index
            batch_size: Number of documents to index per batch

        Returns:
            True if successful, False otherwise
        """
        if not documents:
            logger.warning("No documents to index")
            return True

        try:
            logger.info(f"Indexing {len(documents)} documents...")

            # Process in batches
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                logger.info(f"Indexing batch {i // batch_size + 1} ({len(batch)} documents)")

                # Add documents to index
                task = self.index.add_documents(batch)
                self.client.wait_for_task(task.task_uid)

                # Check task status
                task_info = self.client.get_task(task.task_uid)
                if task_info.status == 'failed':
                    logger.error(f"Indexing batch failed: {task_info.error}")
                    return False

            logger.info(f"Successfully indexed {len(documents)} documents")
            return True

        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            return False

    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the index.

        Args:
            document_id: ID of document to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            task = self.index.delete_document(document_id)
            self.client.wait_for_task(task.task_uid)
            logger.info(f"Deleted document: {document_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False

    def delete_documents_by_filter(self, filter_query: str) -> bool:
        """
        Delete documents matching a filter.

        Args:
            filter_query: Meilisearch filter string (e.g., "user_id = 'user123'")

        Returns:
            True if successful, False otherwise
        """
        try:
            task = self.index.delete_documents_by_filter(filter_query)
            self.client.wait_for_task(task.task_uid)
            logger.info(f"Deleted documents matching filter: {filter_query}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents by filter: {e}")
            return False

    def search(self, query: str, filters: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search documents in the index.

        Args:
            query: Search query string
            filters: Optional filter string
            limit: Maximum number of results

        Returns:
            List of matching documents
        """
        try:
            search_params = {
                'limit': limit
            }
            if filters:
                search_params['filter'] = filters

            results = self.index.search(query, search_params)
            return results['hits']

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        try:
            stats = self.index.get_stats()
            return stats
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
