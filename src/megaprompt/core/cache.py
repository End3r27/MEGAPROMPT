"""Caching system for intermediate pipeline results."""

import hashlib
import json
from pathlib import Path
from typing import Any, Optional


class Cache:
    """Cache manager for pipeline results."""

    def __init__(self, cache_dir: Path):
        """Initialize cache with directory."""
        self.cache_dir = cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)

    def _hash_key(self, key: str) -> str:
        """Generate hash for cache key."""
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for key."""
        key_hash = self._hash_key(key)
        return self.cache_dir / f"{key_hash}.json"

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None

        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            return data.get("value")
        except Exception:
            return None

    def set(self, key: str, value: Any, metadata: Optional[dict[str, Any]] = None) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            metadata: Optional metadata to store with cache entry
        """
        cache_path = self._get_cache_path(key)
        cache_data = {"value": value}
        if metadata:
            cache_data["metadata"] = metadata

        try:
            cache_path.write_text(json.dumps(cache_data, indent=2), encoding="utf-8")
        except Exception:
            pass  # Silently fail on cache write errors

    def delete(self, key: str) -> bool:
        """
        Delete cache entry.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()
            return True
        return False

    def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries deleted
        """
        deleted = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                deleted += 1
            except Exception:
                pass
        return deleted

    def get_cache_key(
        self,
        stage: str,
        input_data: Any,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Generate cache key for stage and input.

        Args:
            stage: Stage name
            input_data: Input data (will be serialized to JSON)
            provider: Optional provider name
            model: Optional model name

        Returns:
            Cache key string
        """
        key_parts = [stage]
        if provider:
            key_parts.append(provider)
        if model:
            key_parts.append(model)

        # Serialize input data
        try:
            input_str = json.dumps(input_data, sort_keys=True)
        except Exception:
            input_str = str(input_data)

        key_parts.append(input_str)
        return "|".join(key_parts)

