"""
Generic Caching Layer for Assistant Skills

Provides a persistent caching mechanism with TTL support, LRU eviction,
pattern-based invalidation, and thread-safe access.

Features:
- SQLite-based persistence for durability
- Category-based TTL defaults
- LRU eviction when cache size limit is reached
- Pattern-based key invalidation (glob patterns with SQL LIKE optimization)
- Thread-safe concurrent access
- Cache hit/miss statistics
"""

import fnmatch
import functools
import hashlib
import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any, Optional


@dataclass
class CacheStats:
    """Cache statistics container."""
    entry_count: int = 0
    total_size_bytes: int = 0
    hits: int = 0
    misses: int = 0
    by_category: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total


def is_simple_glob_pattern(pattern: str) -> bool:
    """
    Check if a glob pattern is simple enough to convert to SQL LIKE.
    """
    # Patterns with character classes or other special glob syntax are not simple
    if any(c in pattern for c in "[]{}"):
        return False
    return True


def glob_to_sql_like(pattern: str) -> tuple[str, bool]:
    """
    Convert a glob pattern to SQL LIKE pattern if possible.
    """
    if not is_simple_glob_pattern(pattern):
        return pattern, False

    sql_pattern = pattern.replace('%', r'\%').replace('_', r'\_')
    sql_pattern = sql_pattern.replace('**/', '%').replace('**', '%').replace('*', '%').replace('?', '_')

    return sql_pattern, True


class SkillCache:
    """
    A generic caching layer for Assistant Skills API responses.
    """

    def __init__(self, cache_name: str = "default", cache_dir: Optional[str] = None, max_size_mb: float = 100):
        """
        Initialize cache.

        SECURITY NOTE: The cache may contain sensitive data from API responses.
        The cache directory is created with restrictive permissions (0700)
        to ensure only the owner can access cached data.

        Args:
            cache_name: A name for the cache database file (e.g., 'jira', 'confluence').
            cache_dir: Directory for cache storage (default: ~/.assistant-skills/cache).
            max_size_mb: Maximum cache size in megabytes (default: 100 MB).
        """
        self.base_cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".assistant-skills" / "cache"
        self.base_cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.base_cache_dir, 0o700)

        self.max_size = int(max_size_mb * 1024 * 1024)
        self.db_path = self.base_cache_dir / f"{cache_name}.db"

        self.ttl_defaults = {
            "default": timedelta(minutes=5),
        }

        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

        self._init_db()

    def set_ttl_defaults(self, defaults: dict[str, timedelta]):
        """
        Set or override TTL defaults for different categories.

        Args:
            defaults: A dictionary mapping category names to timedelta objects.
        """
        self.ttl_defaults.update(defaults)

    def _init_db(self) -> None:
        """Initialize SQLite database for cache storage."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT NOT NULL,
                    category TEXT NOT NULL,
                    value TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    last_accessed_at REAL NOT NULL,
                    PRIMARY KEY (key, category)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_category ON cache_entries(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_entries(expires_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_lru ON cache_entries(last_accessed_at)")
            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Get thread-safe database connection."""
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def get(self, key: str, category: str = "default") -> Optional[Any]:
        """
        Get cached value if not expired.
        """
        with self._lock:
            now = time.time()
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT value, expires_at FROM cache_entries WHERE key = ? AND category = ?", (key, category))
                row = cursor.fetchone()

                if row is None:
                    self._misses += 1
                    return None

                if row["expires_at"] < now:
                    conn.execute("DELETE FROM cache_entries WHERE key = ? AND category = ?", (key, category))
                    conn.commit()
                    self._misses += 1
                    return None

                conn.execute("UPDATE cache_entries SET last_accessed_at = ? WHERE key = ? AND category = ?", (now, key, category))
                conn.commit()
                self._hits += 1
                return json.loads(row["value"])

    def set(self, key: str, value: Any, category: str = "default", ttl: Optional[timedelta] = None) -> None:
        """
        Set cache value with optional custom TTL.
        """
        with self._lock:
            if ttl is None:
                ttl = self.ttl_defaults.get(category, self.ttl_defaults["default"])

            now = time.time()
            expires_at = now + ttl.total_seconds()
            value_json = json.dumps(value)
            size_bytes = len(value_json.encode('utf-8'))

            if size_bytes > self.max_size:
                raise ValueError(f"Cache entry size ({size_bytes} bytes) exceeds maximum cache size ({self.max_size} bytes).")

            self._evict_if_needed(size_bytes)

            with self._get_connection() as conn:
                conn.execute("INSERT OR REPLACE INTO cache_entries (key, category, value, size_bytes, created_at, expires_at, last_accessed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (key, category, value_json, size_bytes, now, expires_at, now))
                conn.commit()

    def _evict_if_needed(self, new_entry_size: int) -> None:
        """Evict entries if adding new entry would exceed size limit."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COALESCE(SUM(size_bytes), 0) as total FROM cache_entries")
            current_size = cursor.fetchone()["total"]

            if current_size + new_entry_size <= self.max_size:
                return

            space_needed = current_size + new_entry_size - self.max_size
            conn.execute("DELETE FROM cache_entries WHERE expires_at < ?", (time.time(),))
            conn.commit()

            cursor = conn.execute("SELECT COALESCE(SUM(size_bytes), 0) as total FROM cache_entries")
            current_size = cursor.fetchone()["total"]

            if current_size + new_entry_size <= self.max_size:
                return

            space_needed = current_size + new_entry_size - self.max_size
            freed = 0
            cursor = conn.execute("SELECT key, category, size_bytes FROM cache_entries ORDER BY last_accessed_at ASC")

            entries_to_delete = []
            for row in cursor:
                if freed >= space_needed:
                    break
                entries_to_delete.append((row["key"], row["category"]))
                freed += row["size_bytes"]

            if entries_to_delete:
                conn.executemany("DELETE FROM cache_entries WHERE key = ? AND category = ?", entries_to_delete)
            conn.commit()

    def invalidate(self, key: Optional[str] = None, pattern: Optional[str] = None, category: Optional[str] = None) -> int:
        """
        Invalidate cache entries.
        """
        with self._lock, self._get_connection() as conn:
            if key is not None and category is not None:
                cursor = conn.execute("DELETE FROM cache_entries WHERE key = ? AND category = ?", (key, category))
            elif pattern is not None:
                sql_pattern, can_use_like = glob_to_sql_like(pattern)
                if can_use_like:
                    query = "DELETE FROM cache_entries WHERE key LIKE ? ESCAPE '\\'"
                    params = [sql_pattern]
                    if category is not None:
                        query += " AND category = ?"
                        params.append(category)
                    cursor = conn.execute(query, params)
                else:
                    query = "SELECT key, category FROM cache_entries"
                    params = []
                    if category is not None:
                        query += " WHERE category = ?"
                        params.append(category)
                    cursor = conn.execute(query, params)
                    to_delete = [(row["key"], row["category"]) for row in cursor if fnmatch.fnmatch(row["key"], pattern)]
                    if to_delete:
                        conn.executemany("DELETE FROM cache_entries WHERE key = ? AND category = ?", to_delete)
                        conn.commit()
                    return len(to_delete)
            elif category is not None:
                cursor = conn.execute("DELETE FROM cache_entries WHERE category = ?", (category,))
            else:
                return 0 # Do nothing if no key, pattern or category is specified

            conn.commit()
            return cursor.rowcount

    def clear(self) -> int:
        """Clear entire cache."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM cache_entries")
            count = cursor.fetchone()["count"]
            conn.execute("DELETE FROM cache_entries")
            conn.commit()
            return count

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock, self._get_connection() as conn:
            stats = CacheStats(hits=self._hits, misses=self._misses)
            cursor = conn.execute("SELECT COUNT(*) as count, COALESCE(SUM(size_bytes), 0) as total_size FROM cache_entries")
            row = cursor.fetchone()
            stats.entry_count = row["count"]
            stats.total_size_bytes = row["total_size"]

            cursor = conn.execute("SELECT category, COUNT(*) as count, SUM(size_bytes) as size FROM cache_entries GROUP BY category")
            for row in cursor:
                stats.by_category[row["category"]] = {"count": row["count"], "size_bytes": row["size"]}
            return stats

    def generate_key(self, category: str, *args: Any, **kwargs: Any) -> str:
        """Generate cache key from arguments."""
        components = [category]
        components.extend(str(arg) for arg in args)
        components.extend(f"{key}={kwargs[key]}" for key in sorted(kwargs.keys()))
        key_str = ":".join(components)

        if len(key_str) > 200:
            hash_suffix = hashlib.md5(key_str.encode()).hexdigest()[:16]
            return f"{category}:{hash_suffix}"
        return key_str

    def close(self) -> None:
        """Close cache (flush any pending operations)."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


def get_skill_cache(cache_name: str, cache_dir: Optional[str] = None, max_size_mb: float = 100) -> SkillCache:
    """
    Get or create a cache instance.
    """
    return SkillCache(cache_name=cache_name, cache_dir=cache_dir, max_size_mb=max_size_mb)


# Backwards-compatible aliases
Cache = SkillCache
get_cache = get_skill_cache


# Global cache registry for the cached decorator
_cache_registry: dict[str, SkillCache] = {}
_cache_registry_lock = threading.Lock()


def _get_default_cache() -> SkillCache:
    """Get or create the default cache instance.

    Thread-safe singleton access using double-checked locking pattern.
    """
    if "default" not in _cache_registry:
        with _cache_registry_lock:
            # Double-check after acquiring lock
            if "default" not in _cache_registry:
                _cache_registry["default"] = SkillCache(cache_name="default")
    return _cache_registry["default"]


def cached(category: str = "default", ttl: Optional[timedelta] = None):
    """
    Decorator to cache function results.

    Args:
        category: Cache category for TTL defaults.
        ttl: Optional custom TTL for cached values.

    Usage:
        @cached(category="api_calls", ttl=timedelta(minutes=10))
        def fetch_data(item_id: str) -> dict:
            return api.get(item_id)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache = _get_default_cache()
            key = cache.generate_key(func.__name__, *args, **kwargs)

            result = cache.get(key, category=category)
            if result is not None:
                return result

            result = func(*args, **kwargs)
            cache.set(key, result, category=category, ttl=ttl)
            return result
        return wrapper
    return decorator


def invalidate(key: Optional[str] = None, pattern: Optional[str] = None, category: Optional[str] = None) -> int:
    """
    Invalidate cache entries in the default cache.

    Args:
        key: Specific key to invalidate.
        pattern: Glob pattern to match keys.
        category: Category to invalidate.

    Returns:
        Number of entries invalidated.
    """
    cache = _get_default_cache()
    return cache.invalidate(key=key, pattern=pattern, category=category)
