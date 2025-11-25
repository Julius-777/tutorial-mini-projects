#!/usr/bin/env python3
"""
Embedding generation module
Supports local sentence-transformers and AWS Bedrock
"""

import logging
from typing import List
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate vector embeddings for text chunks."""

    def __init__(self, model_id: str = "sentence-transformers/all-MiniLM-L6-v2", provider: str = "local"):
        """
        Initialize embedding generator.

        Args:
            model_id: Model identifier (sentence-transformers model name or Bedrock model ID)
            provider: 'local' for sentence-transformers or 'bedrock' for AWS Bedrock
        """
        self.model_id = model_id
        self.provider = provider
        self.model = None

        if provider == "local":
            self._init_local_model()
        elif provider == "bedrock":
            self._init_bedrock()
        else:
            raise ValueError(f"Unknown embedding provider: {provider}")

    def _init_local_model(self):
        """Initialize local sentence-transformers model."""
        try:
            logger.info(f"Loading local embedding model: {self.model_id}")
            self.model = SentenceTransformer(self.model_id)
            logger.info(f"Model loaded successfully. Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
        except Exception as e:
            logger.error(f"Failed to load local model: {e}")
            raise

    def _init_bedrock(self):
        """Initialize AWS Bedrock client."""
        try:
            import boto3
            from config import get_config

            config = get_config()
            logger.info("Initializing AWS Bedrock client")

            # Create Bedrock runtime client
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=config.get('bedrock.region', 'us-east-1'),
                aws_access_key_id=config.get('bedrock.access_key'),
                aws_secret_access_key=config.get('bedrock.secret_key')
            )
            logger.info("Bedrock client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock: {e}")
            raise

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        if self.provider == "local":
            return self._embed_local(texts)
        elif self.provider == "bedrock":
            return self._embed_bedrock(texts)

    def _embed_local(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using local model."""
        try:
            embeddings = self.model.encode(texts, show_progress_bar=False)
            # Convert to list of lists
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    def _embed_bedrock(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using AWS Bedrock."""
        import json

        embeddings = []

        try:
            for text in texts:
                # Call Bedrock Titan Embeddings
                body = json.dumps({"inputText": text})
                response = self.bedrock_client.invoke_model(
                    modelId=self.model_id,
                    body=body
                )

                response_body = json.loads(response['body'].read())
                embedding = response_body.get('embedding')

                if embedding:
                    embeddings.append(embedding)
                else:
                    logger.error(f"No embedding in response for text: {text[:50]}...")
                    # Return zero vector as fallback
                    embeddings.append([0.0] * 1536)

            return embeddings

        except Exception as e:
            logger.error(f"Bedrock embedding generation failed: {e}")
            raise

    def embed_single(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector
        """
        embeddings = self.embed([text])
        return embeddings[0] if embeddings else []

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        if self.provider == "local":
            return self.model.get_sentence_embedding_dimension()
        elif self.provider == "bedrock":
            # Titan embeddings are 1536 dimensions
            return 1536
        return 384  # Default for MiniLM
