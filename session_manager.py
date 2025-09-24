"""
session_manager.py - Session management s MD5 hash cachingem
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime

from models import SampleMetadata

logger = logging.getLogger(__name__)


class SessionManager:
    """Správce session souborů s hash-based cachingem."""

    def __init__(self, sessions_folder: Path = None):
        """
        Inicializuje session manager.

        Args:
            sessions_folder: Složka pro ukládání session souborů (default: ./sessions)
        """
        self.sessions_folder = sessions_folder or Path("sessions")
        self.sessions_folder.mkdir(exist_ok=True)

        self.current_session = None
        self.session_data = None

    def get_available_sessions(self) -> List[str]:
        """Vrátí seznam dostupných session souborů."""
        session_files = list(self.sessions_folder.glob("session-*.json"))
        session_names = []

        for file_path in session_files:
            # Extrahuj název ze souboru session-<name>.json
            name = file_path.stem[8:]  # Odstraň "session-" prefix
            session_names.append(name)

        return sorted(session_names)

    def create_new_session(self, session_name: str) -> bool:
        """
        Vytvoří novou session.

        Args:
            session_name: Název nové session

        Returns:
            True pokud se podařilo vytvořit, False pokud už existuje
        """
        session_file = self._get_session_file(session_name)

        if session_file.exists():
            return False

        # Vytvoř prázdnou session strukturu
        self.session_data = {
            "session_name": session_name,
            "created": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            "folders": {
                "input": None,
                "output": None
            },
            "samples_cache": {},  # hash -> sample data
            "mapping": {},  # "midi,velocity" -> hash
            "settings": {
                "amplitude_filter": None,
                "ui_state": {}
            }
        }

        self.current_session = session_name
        self._save_session()

        logger.info(f"Created new session: {session_name}")
        return True

    def load_session(self, session_name: str) -> bool:
        """
        Načte existující session.

        Args:
            session_name: Název session k načtení

        Returns:
            True pokud se podařilo načíst
        """
        session_file = self._get_session_file(session_name)

        if not session_file.exists():
            logger.error(f"Session file not found: {session_file}")
            return False

        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                self.session_data = json.load(f)

            self.current_session = session_name

            # Update last access time
            self.session_data["last_modified"] = datetime.now().isoformat()
            self._save_session()

            logger.info(f"Loaded session: {session_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load session {session_name}: {e}")
            return False

    def analyze_folder_with_cache(self, input_folder: Path, samples: List[SampleMetadata]) -> Tuple[
        List[SampleMetadata], List[SampleMetadata]]:
        """
        Analyzuje samples s použitím cache.

        Args:
            input_folder: Vstupní složka se samples
            samples: Seznam SampleMetadata objektů k analýze

        Returns:
            Tuple[cached_samples, samples_to_analyze]
        """
        if not self.session_data:
            return [], samples

        # Update input folder
        self.session_data["folders"]["input"] = str(input_folder)

        cached_samples = []
        samples_to_analyze = []

        for sample in samples:
            try:
                # Spočítej MD5 hash
                file_hash = self._calculate_file_hash(sample.filepath)

                # Zkontroluj cache
                if file_hash in self.session_data["samples_cache"]:
                    cached_data = self.session_data["samples_cache"][file_hash]

                    # Obnovit sample data z cache
                    sample.detected_midi = cached_data.get("detected_midi")
                    sample.detected_frequency = cached_data.get("detected_frequency")
                    sample.pitch_confidence = cached_data.get("pitch_confidence", 0.0)
                    sample.pitch_method = cached_data.get("pitch_method", "cached")
                    sample.velocity_amplitude = cached_data.get("velocity_amplitude")
                    sample.velocity_amplitude_db = cached_data.get("velocity_amplitude_db")
                    sample.velocity_duration_ms = cached_data.get("velocity_duration_ms")
                    sample.analyzed = True

                    # Add hash to sample for later reference
                    sample._hash = file_hash

                    cached_samples.append(sample)
                    logger.debug(f"Cache hit: {sample.filename}")

                else:
                    # Add hash to sample for later caching
                    sample._hash = file_hash
                    samples_to_analyze.append(sample)
                    logger.debug(f"Cache miss: {sample.filename}")

            except Exception as e:
                logger.warning(f"Hash calculation failed for {sample.filename}: {e}")
                samples_to_analyze.append(sample)

        logger.info(f"Cache analysis: {len(cached_samples)} cached, {len(samples_to_analyze)} to analyze")
        return cached_samples, samples_to_analyze

    def cache_analyzed_samples(self, samples: List[SampleMetadata]):
        """
        Uloží analyzované samples do cache.

        Args:
            samples: Seznam analyzovaných samples
        """
        if not self.session_data:
            return

        for sample in samples:
            if hasattr(sample, '_hash') and sample.analyzed:
                file_hash = sample._hash

                cache_entry = {
                    "filename": sample.filename,
                    "file_path": str(sample.filepath),
                    "file_size": sample.filepath.stat().st_size if sample.filepath.exists() else 0,
                    "detected_midi": sample.detected_midi,
                    "detected_frequency": sample.detected_frequency,
                    "pitch_confidence": sample.pitch_confidence,
                    "pitch_method": sample.pitch_method,
                    "velocity_amplitude": sample.velocity_amplitude,
                    "velocity_amplitude_db": sample.velocity_amplitude_db,
                    "velocity_duration_ms": sample.velocity_duration_ms,
                    "analyzed_timestamp": datetime.now().isoformat()
                }

                self.session_data["samples_cache"][file_hash] = cache_entry
                logger.debug(f"Cached: {sample.filename}")

        self._save_session()
        logger.info(f"Cached {len(samples)} analyzed samples")

    def save_mapping(self, mapping: Dict[Tuple[int, int], SampleMetadata]):
        """
        Uloží mapping do session.

        Args:
            mapping: Dictionary (midi, velocity) -> SampleMetadata
        """
        if not self.session_data:
            return

        # Convert mapping to hash-based format
        session_mapping = {}
        for (midi, velocity), sample in mapping.items():
            if hasattr(sample, '_hash'):
                key = f"{midi},{velocity}"
                session_mapping[key] = sample._hash
            else:
                logger.warning(f"Sample {sample.filename} has no hash, skipping mapping save")

        self.session_data["mapping"] = session_mapping
        self._save_session()
        logger.info(f"Saved mapping: {len(session_mapping)} entries")

    def restore_mapping(self, all_samples: List[SampleMetadata]) -> Dict[Tuple[int, int], SampleMetadata]:
        """
        Obnoví mapping ze session.

        Args:
            all_samples: Všechny dostupné samples

        Returns:
            Dictionary (midi, velocity) -> SampleMetadata
        """
        if not self.session_data or not self.session_data.get("mapping"):
            return {}

        # Vytvoř hash->sample lookup
        hash_to_sample = {}
        for sample in all_samples:
            if hasattr(sample, '_hash'):
                hash_to_sample[sample._hash] = sample

        # Restore mapping
        restored_mapping = {}
        session_mapping = self.session_data["mapping"]

        for key, file_hash in session_mapping.items():
            try:
                midi_str, velocity_str = key.split(',')
                midi = int(midi_str)
                velocity = int(velocity_str)

                if file_hash in hash_to_sample:
                    sample = hash_to_sample[file_hash]
                    sample.mapped = True
                    restored_mapping[(midi, velocity)] = sample
                else:
                    logger.warning(f"Sample with hash {file_hash} not found for mapping {key}")

            except Exception as e:
                logger.error(f"Failed to restore mapping entry {key}: {e}")

        logger.info(f"Restored mapping: {len(restored_mapping)} entries")
        return restored_mapping

    def save_folders(self, input_folder: Path = None, output_folder: Path = None):
        """Uloží cesty ke složkám."""
        if not self.session_data:
            return

        if input_folder:
            self.session_data["folders"]["input"] = str(input_folder)
        if output_folder:
            self.session_data["folders"]["output"] = str(output_folder)

        self._save_session()

    def get_folders(self) -> Tuple[Optional[Path], Optional[Path]]:
        """Vrátí uložené cesty ke složkám."""
        if not self.session_data:
            return None, None

        folders = self.session_data.get("folders", {})
        input_path = Path(folders["input"]) if folders.get("input") else None
        output_path = Path(folders["output"]) if folders.get("output") else None

        return input_path, output_path

    def get_session_info(self) -> Optional[Dict]:
        """Vrátí informace o aktuální session."""
        if not self.session_data:
            return None

        return {
            "name": self.session_data.get("session_name"),
            "created": self.session_data.get("created"),
            "last_modified": self.session_data.get("last_modified"),
            "cached_samples": len(self.session_data.get("samples_cache", {})),
            "mapping_entries": len(self.session_data.get("mapping", {}))
        }

    def _get_session_file(self, session_name: str) -> Path:
        """Vrátí cestu k session souboru."""
        return self.sessions_folder / f"session-{session_name}.json"

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Spočítá MD5 hash celého souboru."""
        hash_md5 = hashlib.md5()

        try:
            with open(file_path, "rb") as f:
                # Čtení po blocích pro úsporu paměti
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()

        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {e}")
            raise

    def _save_session(self):
        """Uloží aktuální session data."""
        if not self.session_data or not self.current_session:
            return

        self.session_data["last_modified"] = datetime.now().isoformat()
        session_file = self._get_session_file(self.current_session)

        try:
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(self.session_data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Session saved: {session_file}")

        except Exception as e:
            logger.error(f"Failed to save session {self.current_session}: {e}")

    def close_session(self):
        """Zavře aktuální session."""
        if self.session_data:
            self._save_session()

        self.current_session = None
        self.session_data = None
        logger.info("Session closed")