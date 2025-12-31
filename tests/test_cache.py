"""Tests for cache module."""

import pytest
from datetime import timedelta
from assistant_skills_lib import Cache, cached, get_cache, invalidate
from assistant_skills_lib.cache import SkillCache, CacheStats


class TestCache:
    """Tests for Cache/SkillCache class."""

    @pytest.fixture
    def temp_cache(self, tmp_path):
        """Create a cache with a temporary directory."""
        return Cache(cache_name="test", cache_dir=str(tmp_path))

    def test_set_and_get(self, temp_cache):
        """Test basic set and get."""
        temp_cache.set("key1", {"value": 123})
        result = temp_cache.get("key1")
        assert result == {"value": 123}

    def test_get_nonexistent(self, temp_cache):
        """Test get nonexistent key."""
        result = temp_cache.get("nonexistent")
        assert result is None

    def test_set_with_category(self, temp_cache):
        """Test set and get with category."""
        temp_cache.set("key1", "value1", category="api")
        result = temp_cache.get("key1", category="api")
        assert result == "value1"
        # Different category should not find it
        result2 = temp_cache.get("key1", category="other")
        assert result2 is None

    def test_invalidate_by_key(self, temp_cache):
        """Test invalidate by key."""
        temp_cache.set("key1", "value1", category="test")
        assert temp_cache.get("key1", category="test") == "value1"
        count = temp_cache.invalidate(key="key1", category="test")
        assert count == 1
        assert temp_cache.get("key1", category="test") is None

    def test_invalidate_by_pattern(self, temp_cache):
        """Test invalidate by pattern."""
        temp_cache.set("user:1", "value1", category="test")
        temp_cache.set("user:2", "value2", category="test")
        temp_cache.set("other:1", "value3", category="test")
        count = temp_cache.invalidate(pattern="user:*", category="test")
        assert count == 2
        assert temp_cache.get("user:1", category="test") is None
        assert temp_cache.get("other:1", category="test") == "value3"

    def test_clear(self, temp_cache):
        """Test clear."""
        temp_cache.set("key1", "value1")
        temp_cache.set("key2", "value2")
        count = temp_cache.clear()
        assert count == 2
        assert temp_cache.get("key1") is None
        assert temp_cache.get("key2") is None

    def test_get_stats(self, temp_cache):
        """Test get_stats."""
        temp_cache.set("key1", "value1")
        temp_cache.get("key1")  # hit
        temp_cache.get("nonexistent")  # miss
        stats = temp_cache.get_stats()
        assert isinstance(stats, CacheStats)
        assert stats.entry_count == 1
        assert stats.hits == 1
        assert stats.misses == 1

    def test_custom_ttl(self, temp_cache):
        """Test custom TTL on set."""
        temp_cache.set("key1", "value1", ttl=timedelta(minutes=10))
        result = temp_cache.get("key1")
        assert result == "value1"

    def test_generate_key(self, temp_cache):
        """Test generate_key."""
        key = temp_cache.generate_key("category", "arg1", "arg2", opt="value")
        assert "category" in key
        assert "arg1" in key
        assert "opt=value" in key

    def test_context_manager(self, tmp_path):
        """Test cache as context manager."""
        with Cache(cache_name="ctx-test", cache_dir=str(tmp_path)) as cache:
            cache.set("key1", "value1")
            assert cache.get("key1") == "value1"


class TestCachedDecorator:
    """Tests for cached decorator."""

    def test_basic_caching(self, tmp_path):
        """Test basic function caching."""
        # Clear any previous cache entries from other tests
        from assistant_skills_lib.cache import _cache_registry
        _cache_registry.clear()

        call_count = 0

        @cached(category="test_decorator")
        def expensive_function_unique(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call - should execute function
        result1 = expensive_function_unique(5)
        assert result1 == 10
        assert call_count == 1

        # Second call - should use cache
        result2 = expensive_function_unique(5)
        assert result2 == 10
        assert call_count == 1  # Still 1, cached

        # Different argument - should execute function
        result3 = expensive_function_unique(10)
        assert result3 == 20
        assert call_count == 2


class TestGetCache:
    """Tests for get_cache function."""

    def test_get_cache_creates_instance(self, tmp_path):
        """Test that get_cache creates a cache instance."""
        cache = get_cache("test-app", cache_dir=str(tmp_path))
        assert isinstance(cache, Cache)

    def test_cache_alias(self):
        """Test that Cache is an alias for SkillCache."""
        assert Cache is SkillCache


class TestInvalidate:
    """Tests for module-level invalidate function."""

    def test_invalidate_with_pattern(self):
        """Test module-level invalidate function."""
        # This uses the default cache
        count = invalidate(pattern="nonexistent:*", category="test")
        assert count == 0  # Nothing to invalidate
