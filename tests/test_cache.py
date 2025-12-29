"""Tests for cache module."""

import pytest
import tempfile
from pathlib import Path
from assistant_skills_lib import Cache, cached, get_cache, invalidate


class TestCache:
    """Tests for Cache class."""

    @pytest.fixture
    def temp_cache(self, tmp_path):
        """Create a cache with a temporary directory."""
        return Cache(app_name="test", cache_dir=tmp_path, default_ttl=300)

    def test_set_and_get(self, temp_cache):
        """Test basic set and get."""
        temp_cache.set("key1", {"value": 123})
        result = temp_cache.get("key1")
        assert result == {"value": 123}

    def test_get_nonexistent(self, temp_cache):
        """Test get nonexistent key."""
        result = temp_cache.get("nonexistent")
        assert result is None

    def test_get_with_default(self, temp_cache):
        """Test get with default value."""
        result = temp_cache.get("nonexistent", default="default")
        assert result == "default"

    def test_delete(self, temp_cache):
        """Test delete."""
        temp_cache.set("key1", "value1")
        assert temp_cache.get("key1") == "value1"
        temp_cache.delete("key1")
        assert temp_cache.get("key1") is None

    def test_clear(self, temp_cache):
        """Test clear."""
        temp_cache.set("key1", "value1")
        temp_cache.set("key2", "value2")
        count = temp_cache.clear()
        assert count == 2
        assert temp_cache.get("key1") is None
        assert temp_cache.get("key2") is None

    def test_stats(self, temp_cache):
        """Test stats."""
        temp_cache.set("key1", "value1")
        stats = temp_cache.stats()
        assert stats["enabled"] is True
        assert stats["entries"] == 1
        assert "cache_dir" in stats

    def test_disabled_cache(self, tmp_path):
        """Test disabled cache."""
        cache = Cache(app_name="test", cache_dir=tmp_path, enabled=False)
        cache.set("key1", "value1")
        assert cache.get("key1") is None

    def test_custom_ttl(self, temp_cache):
        """Test custom TTL on set."""
        temp_cache.set("key1", "value1", ttl=60)
        result = temp_cache.get("key1")
        assert result == "value1"


class TestCachedDecorator:
    """Tests for cached decorator."""

    def test_basic_caching(self, tmp_path):
        """Test basic function caching."""
        call_count = 0
        cache = Cache(app_name="test-decorator", cache_dir=tmp_path)

        @cached(ttl=300, cache=cache)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call - should execute function
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call - should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Still 1, cached

        # Different argument - should execute function
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count == 2


class TestGetCache:
    """Tests for get_cache function."""

    def test_get_cache_creates_instance(self):
        """Test that get_cache creates a cache instance."""
        cache = get_cache("test-app")
        assert isinstance(cache, Cache)
        assert cache.app_name == "test-app"

    def test_get_cache_returns_same_instance(self):
        """Test that get_cache returns the same instance for same app."""
        cache1 = get_cache("test-app-same")
        cache2 = get_cache("test-app-same")
        assert cache1 is cache2
