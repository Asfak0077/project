"""
In-Memory TTL Response Cache for Specification Queries.

Eliminates redundant MySQL lookups for identical (product_id, spec_field) queries.
Cache entries expire after TTL_SECONDS. Thread-safe via dict + timestamp check.

Usage:
    from services.response_cache import spec_cache

    # Check cache
    cached = spec_cache.get(product_id=3, spec_field="price")
    if cached:
        return cached

    # ... compute answer ...

    # Store in cache
    spec_cache.put(product_id=3, spec_field="price", response=answer_dict)
"""
from __future__ import annotations

import time
import threading
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("backend.response_cache")

DEFAULT_TTL_SECONDS = 300  # 5 minutes


class _CacheEntry:
    __slots__ = ("response", "created_at")

    def __init__(self, response: Dict[str, Any]):
        self.response = response
        self.created_at = time.monotonic()

    def is_expired(self, ttl: float) -> bool:
        return (time.monotonic() - self.created_at) > ttl


class SpecResponseCache:
    """Thread-safe in-memory cache keyed by (product_id, spec_field)."""

    def __init__(self, ttl_seconds: float = DEFAULT_TTL_SECONDS, max_size: int = 500):
        self._store: Dict[str, _CacheEntry] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _key(product_id: Any, spec_field: str) -> str:
        return f"{product_id}:{spec_field}"

    def get(self, product_id: Any, spec_field: str) -> Optional[Dict[str, Any]]:
        """Return cached response if present and not expired, else None."""
        key = self._key(product_id, spec_field)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired(self._ttl):
                del self._store[key]
                self._misses += 1
                return None
            self._hits += 1
            return entry.response

    def put(self, product_id: Any, spec_field: str, response: Dict[str, Any]) -> None:
        """Store a response in the cache."""
        key = self._key(product_id, spec_field)
        with self._lock:
            # Evict expired entries if approaching max size
            if len(self._store) >= self._max_size:
                self._evict_expired()
            # If still at capacity, drop oldest entry
            if len(self._store) >= self._max_size:
                oldest_key = min(self._store, key=lambda k: self._store[k].created_at)
                del self._store[oldest_key]
            self._store[key] = _CacheEntry(response)

    def invalidate(self, product_id: Any, spec_field: Optional[str] = None) -> None:
        """Invalidate cache entries for a product. If spec_field is None, invalidate all fields."""
        prefix = f"{product_id}:"
        with self._lock:
            if spec_field:
                self._store.pop(self._key(product_id, spec_field), None)
            else:
                keys_to_remove = [k for k in self._store if k.startswith(prefix)]
                for k in keys_to_remove:
                    del self._store[k]

    def clear(self) -> None:
        """Clear the entire cache."""
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    def _evict_expired(self) -> None:
        """Remove all expired entries (must hold lock)."""
        expired = [k for k, v in self._store.items() if v.is_expired(self._ttl)]
        for k in expired:
            del self._store[k]

    @property
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "size": len(self._store),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / max(self._hits + self._misses, 1) * 100, 1),
            }


# Module-level singleton
spec_cache = SpecResponseCache()
