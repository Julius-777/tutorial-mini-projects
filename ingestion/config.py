#!/usr/bin/env python3
"""
Configuration loader for Ingestion Service
Reads config.yaml and environment variables
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for ingestion service."""

    def __init__(self, config_path: str = None):
        """
        Load configuration from yaml file and environment variables.

        Args:
            config_path: Path to config.yaml file (defaults to CONFIG_PATH env var)
        """
        self.config_path = config_path or os.getenv('CONFIG_PATH', '/app/config.yaml')
        self.config = self._load_yaml()
        self._merge_env_vars()

    def _load_yaml(self) -> Dict[str, Any]:
        """Load YAML configuration file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    logger.info(f"Loaded configuration from {self.config_path}")
                    return config
            else:
                logger.warning(f"Config file not found: {self.config_path}, using defaults")
                return {}
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            return {}

    def _merge_env_vars(self):
        """Merge environment variables into configuration."""
        # Meilisearch
        if os.getenv('MEILI_HOST'):
            self.config.setdefault('services', {}).setdefault('meilisearch', {})['host'] = os.getenv('MEILI_HOST')
        if os.getenv('MEILI_MASTER_KEY'):
            self.config.setdefault('services', {}).setdefault('meilisearch', {})['master_key'] = os.getenv('MEILI_MASTER_KEY')

        # MongoDB
        if os.getenv('MONGO_CONNECTION_STRING'):
            self.config.setdefault('services', {}).setdefault('mongodb', {})['connection_string'] = os.getenv('MONGO_CONNECTION_STRING')

        # Microservices
        if os.getenv('CONVERTER_SERVICE_URL'):
            self.config.setdefault('services', {}).setdefault('converter', {})['url'] = os.getenv('CONVERTER_SERVICE_URL')
        if os.getenv('OCR_SERVICE_URL'):
            self.config.setdefault('services', {}).setdefault('ocr', {})['url'] = os.getenv('OCR_SERVICE_URL')

        # AWS Bedrock
        if os.getenv('BEDROCK_ACCESS_KEY'):
            self.config.setdefault('bedrock', {})['access_key'] = os.getenv('BEDROCK_ACCESS_KEY')
        if os.getenv('BEDROCK_SECRET_KEY'):
            self.config.setdefault('bedrock', {})['secret_key'] = os.getenv('BEDROCK_SECRET_KEY')
        if os.getenv('BEDROCK_REGION'):
            self.config.setdefault('bedrock', {})['region'] = os.getenv('BEDROCK_REGION')

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key_path: Dot-separated path (e.g., 'services.meilisearch.host')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    # Convenience properties
    @property
    def meilisearch_host(self) -> str:
        return self.get('services.meilisearch.host', 'http://meilisearch:7700')

    @property
    def meilisearch_key(self) -> str:
        return self.get('services.meilisearch.master_key', os.getenv('MEILI_MASTER_KEY', ''))

    @property
    def meilisearch_index(self) -> str:
        return self.get('services.meilisearch.index_name', 'document-index')

    @property
    def mongodb_connection(self) -> str:
        return self.get('services.mongodb.connection_string', os.getenv('MONGO_CONNECTION_STRING', 'mongodb://mongo:27017/pdf-search-app'))

    @property
    def mongodb_database(self) -> str:
        return self.get('services.mongodb.database_name', 'pdf-search-app')

    @property
    def converter_url(self) -> str:
        base = self.get('services.converter.url', 'http://converter:3000')
        endpoint = self.get('services.converter.endpoint', '/convert')
        return f"{base}{endpoint}"

    @property
    def ocr_url(self) -> str:
        base = self.get('services.ocr.url', 'http://ocr:3000')
        endpoint = self.get('services.ocr.endpoint', '/ocr')
        return f"{base}{endpoint}"

    @property
    def embedding_model(self) -> str:
        return self.get('rag.embedding.model_id', 'sentence-transformers/all-MiniLM-L6-v2')

    @property
    def embedding_provider(self) -> str:
        return self.get('rag.embedding.provider', 'local')

    @property
    def chunk_size(self) -> int:
        return self.get('rag.chunking.chunk_size', 1000)

    @property
    def chunk_overlap(self) -> int:
        return self.get('rag.chunking.chunk_overlap', 200)

    @property
    def chunking_strategy(self) -> str:
        return self.get('rag.chunking.strategy', 'hierarchical')


# Global config instance
_config = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
