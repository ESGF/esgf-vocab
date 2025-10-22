"""Caching for resolved JSON-LD terms to improve performance."""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class TermCache:
    """
    LRU cache for JSON-LD terms fetched from files or remote sources.

    Caching reduces redundant file I/O and network calls when the same
    terms are referenced multiple times during resolution.
    """

    def __init__(self, max_size: int = 128, enabled: bool = True):
        """
        Initialize the term cache.

        Args:
            max_size: Maximum number of terms to cache
            enabled: Whether caching is enabled (can be disabled for debugging)
        """
        self.max_size = max_size
        self.enabled = enabled
        self._cache: Dict[str, dict] = {}
        self._hits = 0
        self._misses = 0

    def get(self, uri: str) -> dict | None:
        """
        Retrieve a cached term by URI.

        Args:
            uri: The URI key for the cached term

        Returns:
            The cached term data, or None if not in cache
        """
        if not self.enabled:
            return None

        if uri in self._cache:
            self._hits += 1
            logger.debug(f"Cache hit for {uri}")
            return self._cache[uri]

        self._misses += 1
        return None

    def put(self, uri: str, data: dict) -> None:
        """
        Store a term in the cache.

        Args:
            uri: The URI key for the term
            data: The term data to cache
        """
        if not self.enabled:
            return

        # Simple LRU: if cache is full, remove the oldest entry
        if len(self._cache) >= self.max_size:
            # Remove first item (oldest in insertion order for Python 3.7+)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            logger.debug(f"Cache eviction: {oldest_key}")

        self._cache[uri] = data
        logger.debug(f"Cached {uri}")

    def clear(self) -> None:
        """Clear all cached terms."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.debug("Cache cleared")

    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache hits, misses, size, and hit rate
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "size": len(self._cache),
            "max_size": self.max_size,
            "hit_rate_percent": round(hit_rate, 2),
        }

    def __repr__(self) -> str:
        """String representation showing cache stats."""
        stats = self.get_stats()
        return (
            f"TermCache(size={stats['size']}/{stats['max_size']}, "
            f"hits={stats['hits']}, misses={stats['misses']}, "
            f"hit_rate={stats['hit_rate_percent']}%)"
        )
