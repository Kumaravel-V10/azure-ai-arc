"""
Shared Services Module - Singleton instances for expensive resources.

Avoids creating duplicate Azure OpenAI clients, rebuilding doc indexes,
and re-initializing analyzers across multiple agents and requests.
"""

import logging
import os
from openai import AsyncAzureOpenAI
from config import azure_openai_config

logger = logging.getLogger(__name__)

# ── Singleton instances ──────────────────────────────────────────────────────

_openai_client: AsyncAzureOpenAI | None = None
_docs_index_built = False


def get_openai_client() -> AsyncAzureOpenAI:
    """Return a shared AsyncAzureOpenAI client (created once)."""
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncAzureOpenAI(
            api_key=azure_openai_config.API_KEY or os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=azure_openai_config.API_VERSION,
            azure_endpoint=azure_openai_config.ENDPOINT or os.getenv("AZURE_OPENAI_ENDPOINT"),
        )
        logger.info("Shared AsyncAzureOpenAI client created")
    return _openai_client


def ensure_docs_index():
    """Build the azure-docs search index exactly once at startup."""
    global _docs_index_built
    if not _docs_index_built:
        try:
            from azure_docs_scanner import get_scanner
            scanner = get_scanner()
            scanner.build_index()
            _docs_index_built = True
            logger.info(f"Azure docs index built: {len(scanner._index)} entries")
        except Exception as e:
            logger.warning(f"Could not build azure-docs index: {e}")
            _docs_index_built = True  # Don't retry on failure
