# -*- coding: utf-8 -*-
import pytest
from pathlib import Path

@pytest.mark.unit
class TestMd5CacheManager:
    def test_cache_initialization(self):
        from src.infrastructure.persistence import Md5CacheManager
        cache = Md5CacheManager()
        assert cache is not None
        stats = cache.get_stats()
        assert stats["total_entries"] == 0
        
    def test_cache_and_retrieve(self):
        from src.infrastructure.persistence import Md5CacheManager
        cache = Md5CacheManager()
        
        test_hash = "abc123"
        test_data = {"detected_midi": 60, "filename": "test.wav"}
        
        cache.cache_analysis(test_hash, test_data)
        retrieved = cache.get_cached_analysis(test_hash)
        
        assert retrieved is not None
        assert retrieved["detected_midi"] == 60
