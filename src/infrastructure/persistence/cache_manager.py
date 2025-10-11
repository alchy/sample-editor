"""
CacheManager - MD5 hash-based caching pro audio sample analysis.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class Md5CacheManager:
    """
    Spravuje MD5 hash-based cache pro audio sample analyzu.
    Umoznuje rychle nacist drive analyzovane samples.
    """

    def __init__(self):
        """Inicializuje cache manager."""
        self._cache: Dict[str, Dict[str, Any]] = {}
        logger.info("Md5CacheManager initialized")

    def get_cached_analysis(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """
        Ziska cached analyzu pro dany hash.
        
        Args:
            file_hash: MD5 hash souboru
            
        Returns:
            Cached data nebo None
        """
        cached_data = self._cache.get(file_hash)
        if cached_data and self._validate_cached_data(cached_data):
            logger.debug(f"Cache hit for hash {file_hash[:8]}...")
            return cached_data
        return None

    def cache_analysis(self, file_hash: str, analysis_data: Dict[str, Any]) -> None:
        """
        Ulozi analysis data do cache.
        
        Args:
            file_hash: MD5 hash souboru
            analysis_data: Data k ulozeni
        """
        # Pridej timestamp a verzi
        analysis_data["analyzed_timestamp"] = datetime.now().isoformat()
        analysis_data["cache_version"] = "2.0"
        
        self._cache[file_hash] = analysis_data
        logger.debug(f"Cached analysis for hash {file_hash[:8]}...")

    def load_cache_from_dict(self, cache_dict: Dict[str, Dict[str, Any]]) -> None:
        """
        Nacte cache ze slovniku (z JSON session).
        
        Args:
            cache_dict: Slovnik s cached daty
        """
        self._cache = cache_dict.copy()
        logger.info(f"Loaded {len(self._cache)} entries from cache")

    def export_cache_to_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        Exportuje cache do slovniku (pro JSON session).
        
        Returns:
            Slovnik s cached daty
        """
        return self._cache.copy()

    def clear(self) -> None:
        """Vycisti celou cache."""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared: {count} entries removed")

    def get_stats(self) -> Dict[str, Any]:
        """
        Vrati statistiky cache.
        
        Returns:
            Dict se statistikami
        """
        import json
        cache_size = len(json.dumps(self._cache))
        
        return {
            "total_entries": len(self._cache),
            "cache_size_bytes": cache_size,
            "cache_size_mb": cache_size / (1024 * 1024)
        }

    def calculate_file_hash(self, file_path: Path) -> str:
        """
        Spocita MD5 hash souboru.
        
        Args:
            file_path: Cesta k souboru
            
        Returns:
            MD5 hash jako hexstring
            
        Raises:
            FileNotFoundError: Pokud soubor neexistuje
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File does not exist: {file_path}")

        hash_md5 = hashlib.md5()

        try:
            with open(file_path, "rb") as f:
                # Cteni po blocich pro usporu pameti
                while chunk := f.read(8192):
                    hash_md5.update(chunk)

            file_hash = hash_md5.hexdigest()
            logger.debug(f"Calculated hash for {file_path.name}: {file_hash[:8]}...")
            return file_hash

        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {e}")
            raise

    def _validate_cached_data(self, cached_data: Dict[str, Any]) -> bool:
        """
        Validuje zda cached data obsahuji potrebne informace.
        
        Args:
            cached_data: Data k validaci
            
        Returns:
            True pokud jsou data validni
        """
        required_keys = ["filename", "analyzed_timestamp"]
        
        for key in required_keys:
            if key not in cached_data:
                logger.warning(f"Missing key '{key}' in cached data")
                return False
        
        # Kontroluj zda jsou pitch nebo amplitude data pritomny
        has_pitch = cached_data.get("detected_midi") is not None
        has_amplitude = cached_data.get("velocity_amplitude") is not None
        
        if not has_pitch and not has_amplitude:
            logger.warning("No analysis data in cache entry")
            return False
        
        return True
