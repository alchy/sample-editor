"""
SessionService - Orchestruje session management, caching a persistence.
"""
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from src.domain.models import SampleMetadata
from src.infrastructure.persistence import Md5CacheManager, JsonSessionRepository

logger = logging.getLogger(__name__)

class SessionService:
    """Business logika pro session management."""
    
    def __init__(self, repository: JsonSessionRepository = None, cache_manager: Md5CacheManager = None):
        self.repository = repository or JsonSessionRepository()
        self.cache = cache_manager or Md5CacheManager()
        self.current_session_name: Optional[str] = None
        self.current_session_data: Optional[Dict[str, Any]] = None
        
    def create_session(self, name: str) -> bool:
        """Vytvori novou session."""
        try:
            session_data = self.repository.create(name)
            self.current_session_name = name
            self.current_session_data = session_data
            self.cache.clear()
            return True
        except ValueError:
            return False
            
    def load_session(self, name: str) -> bool:
        """Nacte session."""
        session_data = self.repository.load(name)
        if session_data:
            self.current_session_name = name
            self.current_session_data = session_data
            self.cache.load_cache_from_dict(session_data.get("samples_cache", {}))
            return True
        return False
        
    def analyze_with_cache(self, samples: List[SampleMetadata]) -> Tuple[List[SampleMetadata], List[SampleMetadata]]:
        """Analyzuje samples s pouzitim cache."""
        cached = []
        to_analyze = []

        logger.info(f"analyze_with_cache: Processing {len(samples)} samples")

        for sample in samples:
            try:
                if not sample.filepath.exists():
                    logger.warning(f"Sample filepath does not exist: {sample.filepath}")
                    continue

                file_hash = self.cache.calculate_file_hash(sample.filepath)
                cached_data = self.cache.get_cached_analysis(file_hash)

                if cached_data:
                    self._restore_sample_from_cache(sample, cached_data, file_hash)
                    cached.append(sample)
                    logger.debug(f"Loaded from cache: {sample.filename}")
                else:
                    sample._hash = file_hash
                    to_analyze.append(sample)
                    logger.debug(f"To analyze: {sample.filename}")
            except Exception as e:
                logger.error(f"Error processing {sample.filename}: {e}", exc_info=True)
                to_analyze.append(sample)

        logger.info(f"analyze_with_cache result: {len(cached)} cached, {len(to_analyze)} to analyze")
        return cached, to_analyze
        
    def cache_analyzed_samples(self, samples: List[SampleMetadata]):
        """Ulozi analyzovane samples do cache."""
        for sample in samples:
            if hasattr(sample, '_hash') and sample.analyzed:
                cache_entry = self._create_cache_entry(sample)
                self.cache.cache_analysis(sample._hash, cache_entry)
                
        if self.current_session_data:
            self.current_session_data["samples_cache"] = self.cache.export_cache_to_dict()
            self.repository.save(self.current_session_name, self.current_session_data)
            
    def _restore_sample_from_cache(self, sample, cached_data, file_hash):
        """Obnovi sample z cache."""
        sample.detected_midi = cached_data.get("detected_midi")
        sample.detected_frequency = cached_data.get("detected_frequency")
        sample.pitch_confidence = cached_data.get("pitch_confidence", 0.0)
        sample.velocity_amplitude = cached_data.get("velocity_amplitude")
        sample.analyzed = True
        sample._hash = file_hash
        
    def _create_cache_entry(self, sample):
        """Vytvori cache entry ze sample."""
        return {
            "filename": sample.filename,
            "detected_midi": int(sample.detected_midi) if sample.detected_midi else None,
            "detected_frequency": float(sample.detected_frequency) if sample.detected_frequency else None,
            "velocity_amplitude": float(sample.velocity_amplitude) if sample.velocity_amplitude else None,
        }
