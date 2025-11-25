#!/usr/bin/env python3
"""
MongoDB client for document metadata storage
Manages users, documents, annotations, and user-document relationships
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from config import get_config

logger = logging.getLogger(__name__)


class MongoDBClient:
    """Client for storing document metadata in MongoDB."""

    def __init__(self):
        """Initialize MongoDB client."""
        config = get_config()
        self.connection_string = config.mongodb_connection
        self.database_name = config.mongodb_database

        logger.info(f"Connecting to MongoDB: {self.database_name}")

        try:
            self.client = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command('ping')
            logger.info("MongoDB connection successful")

            self.db = self.client[self.database_name]
            self._setup_collections()

        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def _setup_collections(self):
        """Setup collections and indexes."""
        # Collection names from Section 6.2 of architecture document
        self.users = self.db['users']
        self.documents = self.db['documents']
        self.annotations = self.db['annotations']
        self.user_doc_meta = self.db['user_doc_meta']

        # Create indexes for better query performance
        self._create_indexes()

    def _create_indexes(self):
        """Create indexes on collections."""
        try:
            # Users collection
            self.users.create_index([('email', ASCENDING)], unique=True)

            # Documents collection
            self.documents.create_index([('owner_id', ASCENDING)])
            self.documents.create_index([('created_at', DESCENDING)])

            # Annotations collection
            self.annotations.create_index([('doc_id', ASCENDING), ('user_id', ASCENDING)])
            self.annotations.create_index([('user_id', ASCENDING)])

            # User-document metadata collection
            self.user_doc_meta.create_index([('user_id', ASCENDING), ('doc_id', ASCENDING)], unique=True)

            logger.info("MongoDB indexes created successfully")

        except Exception as e:
            logger.warning(f"Index creation warning: {e}")

    # =========================================================================
    # Document Operations
    # =========================================================================

    def create_document(self, doc_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a new document record.

        Args:
            doc_data: Document metadata (title, owner_id, s3_url, etc.)

        Returns:
            Document ID if successful, None otherwise
        """
        try:
            # Add timestamp
            doc_data['created_at'] = datetime.utcnow()
            doc_data['last_modified'] = datetime.utcnow()

            result = self.documents.insert_one(doc_data)
            doc_id = str(result.inserted_id)

            logger.info(f"Created document: {doc_id}")
            return doc_id

        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            return None

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document by ID.

        Args:
            doc_id: Document ID

        Returns:
            Document data or None
        """
        try:
            from bson.objectid import ObjectId
            doc = self.documents.find_one({'_id': ObjectId(doc_id)})
            if doc:
                doc['_id'] = str(doc['_id'])
            return doc
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            return None

    def update_document(self, doc_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update document metadata.

        Args:
            doc_id: Document ID
            updates: Fields to update

        Returns:
            True if successful, False otherwise
        """
        try:
            from bson.objectid import ObjectId

            # Add last_modified timestamp
            updates['last_modified'] = datetime.utcnow()

            result = self.documents.update_one(
                {'_id': ObjectId(doc_id)},
                {'$set': updates}
            )

            if result.modified_count > 0:
                logger.info(f"Updated document: {doc_id}")
                return True
            else:
                logger.warning(f"No document updated: {doc_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            return False

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete document and all related data.

        Args:
            doc_id: Document ID

        Returns:
            True if successful, False otherwise
        """
        try:
            from bson.objectid import ObjectId

            # Delete document
            self.documents.delete_one({'_id': ObjectId(doc_id)})

            # Delete related annotations
            self.annotations.delete_many({'doc_id': doc_id})

            # Delete user-document metadata
            self.user_doc_meta.delete_many({'doc_id': doc_id})

            logger.info(f"Deleted document and related data: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False

    # =========================================================================
    # User-Document Metadata Operations
    # =========================================================================

    def create_user_doc_meta(self, user_id: str, doc_id: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Create user-document relationship metadata.

        Args:
            user_id: User ID
            doc_id: Document ID
            metadata: Optional metadata (tags, folder_path, etc.)

        Returns:
            True if successful, False otherwise
        """
        try:
            doc_meta = {
                'user_id': user_id,
                'doc_id': doc_id,
                'created_at': datetime.utcnow(),
                'tags': metadata.get('tags', []) if metadata else [],
                'folder_path': metadata.get('folder_path', '/') if metadata else '/',
            }

            self.user_doc_meta.insert_one(doc_meta)
            logger.info(f"Created user-doc metadata: user={user_id}, doc={doc_id}")
            return True

        except DuplicateKeyError:
            logger.warning(f"User-doc metadata already exists: user={user_id}, doc={doc_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to create user-doc metadata: {e}")
            return False

    def add_tags(self, user_id: str, doc_id: str, tags: list) -> bool:
        """
        Add tags to a document for a specific user.

        Args:
            user_id: User ID
            doc_id: Document ID
            tags: List of tag strings

        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.user_doc_meta.update_one(
                {'user_id': user_id, 'doc_id': doc_id},
                {'$addToSet': {'tags': {'$each': tags}}}
            )

            if result.modified_count > 0:
                logger.info(f"Added tags to doc {doc_id} for user {user_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to add tags: {e}")
            return False

    # =========================================================================
    # Annotation Operations (for future use by API service)
    # =========================================================================

    def create_annotation(self, annotation_data: Dict[str, Any]) -> Optional[str]:
        """
        Create an annotation.

        Args:
            annotation_data: Annotation data (type, color, page, coordinates, etc.)

        Returns:
            Annotation ID if successful, None otherwise
        """
        try:
            annotation_data['created_at'] = datetime.utcnow()
            result = self.annotations.insert_one(annotation_data)
            annotation_id = str(result.inserted_id)

            logger.info(f"Created annotation: {annotation_id}")
            return annotation_id

        except Exception as e:
            logger.error(f"Failed to create annotation: {e}")
            return None

    def get_annotations(self, doc_id: str, user_id: str) -> list:
        """
        Get all annotations for a document and user.

        Args:
            doc_id: Document ID
            user_id: User ID

        Returns:
            List of annotations
        """
        try:
            annotations = list(self.annotations.find({
                'doc_id': doc_id,
                'user_id': user_id
            }))

            # Convert ObjectId to string
            for anno in annotations:
                anno['_id'] = str(anno['_id'])

            return annotations

        except Exception as e:
            logger.error(f"Failed to get annotations: {e}")
            return []

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
