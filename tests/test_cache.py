import pytest
import os
import time
import sqlite3
from pathlib import Path
from datetime import timedelta
from unittest.mock import patch

from assistant_skills_lib.cache import SkillCache, get_skill_cache, CacheStats

@pytest.fixture
def cache_instance(tmp_path):
    """Fixture to create a SkillCache instance with a temporary directory."""
    cache = SkillCache(cache_name="test_cache", cache_dir=str(tmp_path))
    yield cache
    cache.clear()

def test_cache_init_creates_files(tmp_path):
    """Test that SkillCache initialization creates the directory and db file."""
    cache_dir = tmp_path / "test_cache_init"
    db_path = cache_dir / "test.db"
    assert not cache_dir.exists()
    
    cache = SkillCache(cache_name="test", cache_dir=str(cache_dir))
    
    assert cache_dir.exists()
    assert db_path.exists()
    # Check directory permissions (should be 0700)
    assert (cache_dir.stat().st_mode & 0o777) == 0o700

def test_set_and_get(cache_instance):
    """Test basic set and get functionality."""
    cache_instance.set("key1", {"data": "value"}, "category1")
    retrieved = cache_instance.get("key1", "category1")
    assert retrieved == {"data": "value"}
    
    # Test getting a non-existent key
    assert cache_instance.get("nonexistent", "category1") is None

def test_cache_expiration(cache_instance):
    """Test that cache entries expire after their TTL."""
    cache_instance.set("key_expire", "data", ttl=timedelta(seconds=0.01))
    time.sleep(0.02)
    assert cache_instance.get("key_expire") is None

def test_category_ttl_defaults(cache_instance):
    """Test that different categories can have different default TTLs."""
    cache_instance.set_ttl_defaults({
        "short": timedelta(seconds=0.01),
        "long": timedelta(hours=1)
    })
    
    cache_instance.set("key_short", "data", category="short")
    cache_instance.set("key_long", "data", category="long")
    
    time.sleep(0.02)
    
    assert cache_instance.get("key_short", "short") is None
    assert cache_instance.get("key_long", "long") is not None

def test_lru_eviction(tmp_path):
    """Test that the least recently used items are evicted when cache is full."""
    # Create a very small cache
    cache = SkillCache(cache_name="lru_test", cache_dir=str(tmp_path), max_size_mb=0.001) # Approx 1KB
    
    cache.set("key1", "a" * 200) # Entry 1
    cache.set("key2", "b" * 200) # Entry 2
    cache.set("key3", "c" * 200) # Entry 3
    
    # Access key1 to make it most recently used
    cache.get("key1")
    
    # This should evict key2 (least recently used)
    cache.set("key4", "d" * 500) 
    
    assert cache.get("key1") is not None
    assert cache.get("key2") is None # Should have been evicted
    assert cache.get("key3") is not None
    assert cache.get("key4") is not None

def test_invalidate_specific_key(cache_instance):
    """Test invalidating a single key."""
    cache_instance.set("key1", "data", "cat1")
    cache_instance.set("key2", "data", "cat1")
    
    assert cache_instance.invalidate(key="key1", category="cat1") == 1
    assert cache_instance.get("key1", "cat1") is None
    assert cache_instance.get("key2", "cat1") is not None

def test_invalidate_by_pattern(cache_instance):
    """Test invalidating keys using a glob pattern."""
    cache_instance.set("proj-1-details", "data", "issues")
    cache_instance.set("proj-1-comments", "data", "issues")
    cache_instance.set("proj-2-details", "data", "issues")
    
    # Test simple pattern with SQL LIKE optimization
    assert cache_instance.invalidate(pattern="proj-1-*", category="issues") == 2
    assert cache_instance.get("proj-1-details", "issues") is None
    assert cache_instance.get("proj-1-comments", "issues") is None
    assert cache_instance.get("proj-2-details", "issues") is not None

def test_invalidate_complex_pattern(cache_instance):
    """Test invalidating keys with a pattern that requires fnmatch."""
    # Use keys without brackets, and a pattern with character class
    cache_instance.set("file1.txt", "data")
    cache_instance.set("file2.txt", "data")
    cache_instance.set("file3.txt", "data")

    # This pattern uses character class [1-2] to match file1.txt and file2.txt
    # The pattern is not simple (contains []), so it will use fnmatch
    assert cache_instance.invalidate(pattern="file[1-2].txt") == 2
    assert cache_instance.get("file1.txt") is None
    assert cache_instance.get("file2.txt") is None
    assert cache_instance.get("file3.txt") is not None


def test_invalidate_by_category(cache_instance):
    """Test invalidating an entire category."""
    cache_instance.set("key1", "data", "cat_A")
    cache_instance.set("key2", "data", "cat_A")
    cache_instance.set("key3", "data", "cat_B")
    
    assert cache_instance.invalidate(category="cat_A") == 2
    assert cache_instance.get("key1", "cat_A") is None
    assert cache_instance.get("key2", "cat_A") is None
    assert cache_instance.get("key3", "cat_B") is not None

def test_clear_cache(cache_instance):
    """Test clearing the entire cache."""
    cache_instance.set("key1", "data", "cat1")
    cache_instance.set("key2", "data", "cat2")
    
    assert cache_instance.clear() == 2
    assert cache_instance.get_stats().entry_count == 0

def test_get_stats(cache_instance):
    """Test cache statistics gathering."""
    cache_instance.set("k1", "data", "c1")
    cache_instance.set("k2", "data", "c1")
    cache_instance.set("k3", "data", "c2")
    
    cache_instance.get("k1", "c1") # Hit
    cache_instance.get("k4", "c1") # Miss
    
    stats = cache_instance.get_stats()
    assert stats.entry_count == 3
    assert stats.hits == 1
    assert stats.misses == 1
    assert stats.hit_rate == 0.5
    assert "c1" in stats.by_category
    assert "c2" in stats.by_category
    assert stats.by_category["c1"]["count"] == 2

def test_generate_key():
    """Test cache key generation."""
    key1 = SkillCache.generate_key(None, "cat", "arg1", kwarg="val")
    key2 = SkillCache.generate_key(None, "cat", "arg1", kwarg="val")
    key3 = SkillCache.generate_key(None, "cat", "arg2", kwarg="val")
    
    assert key1 == "cat:arg1:kwarg=val"
    assert key1 == key2
    assert key1 != key3

def test_generate_key_hashing():
    """Test that long keys are hashed."""
    long_arg = "a" * 300
    key = SkillCache.generate_key(None, "long_cat", long_arg)
    assert len(key) < 100
    assert key.startswith("long_cat:")
    assert key != f"long_cat:{long_arg}"
    
def test_get_skill_cache_factory():
    """Test the get_skill_cache factory function."""
    cache1 = get_skill_cache("my_cache")
    cache2 = get_skill_cache("my_cache")
    
    assert isinstance(cache1, SkillCache)
    assert cache1.db_path.name == "my_cache.db"
    # The factory doesn't guarantee singletons, just correct instantiation
    assert cache1 is not cache2