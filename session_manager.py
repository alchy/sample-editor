"""
session_manager.py - Opravený Session management s MD5 hash cachingem
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

        # Pro kompatibilitu s novým refaktorovaným kódem
        # Vytvoř "cache" atribut který deleguje na self
        self.cache = self  # SessionManager sám implementuje cache metody

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

    def analyze_with_cache(self, samples: List[SampleMetadata]) -> Tuple[
        List[SampleMetadata], List[SampleMetadata]]:
        """
        KOMPATIBILNÍ METODA: Analyzuje samples s použitím cache (bez input_folder).

        Tato metoda je pro kompatibilitu s novým refaktorovaným kódem.
        Input folder se extrahuje z prvního sample.

        Args:
            samples: Seznam SampleMetadata objektů k analýze

        Returns:
            Tuple[cached_samples, samples_to_analyze]
        """
        if not samples:
            return [], []

        # Extrahuj input folder z prvního sample
        input_folder = samples[0].filepath.parent
        return self.analyze_folder_with_cache(input_folder, samples)

    def analyze_folder_with_cache(self, input_folder: Path, samples: List[SampleMetadata]) -> Tuple[
        List[SampleMetadata], List[SampleMetadata]]:
        """
        OPRAVENÁ METODA: Analyzuje samples s použitím cache.

        Args:
            input_folder: Vstupní složka se samples
            samples: Seznam SampleMetadata objektů k analýze

        Returns:
            Tuple[cached_samples, samples_to_analyze]
        """
        if not self.session_data:
            logger.warning("No session data available for caching")
            return [], samples

        # Update input folder
        self.session_data["folders"]["input"] = str(input_folder)

        cached_samples = []
        samples_to_analyze = []

        logger.info(f"Checking cache for {len(samples)} samples...")

        for sample in samples:
            try:
                # OPRAVA: Kontroluj zda soubor existuje před hash výpočtem
                if not sample.filepath.exists():
                    logger.warning(f"File does not exist: {sample.filepath}")
                    continue

                # Spočítej MD5 hash
                file_hash = self._calculate_file_hash(sample.filepath)
                logger.debug(f"Calculated hash for {sample.filename}: {file_hash[:8]}...")

                # Zkontroluj cache
                if file_hash in self.session_data["samples_cache"]:
                    cached_data = self.session_data["samples_cache"][file_hash]

                    # OPRAVA: Validuj že cached data obsahují potřebné klíče
                    if self._validate_cached_data(cached_data, sample.filename):
                        # Obnovit sample data z cache
                        self._restore_sample_from_cache(sample, cached_data, file_hash)
                        cached_samples.append(sample)
                        logger.debug(f"Cache hit: {sample.filename}")
                    else:
                        logger.warning(f"Invalid cached data for {sample.filename}, will re-analyze")
                        sample._hash = file_hash
                        samples_to_analyze.append(sample)
                else:
                    # Cache miss - přidej hash pro pozdější caching
                    sample._hash = file_hash
                    samples_to_analyze.append(sample)
                    logger.debug(f"Cache miss: {sample.filename}")

            except Exception as e:
                logger.error(f"Hash calculation failed for {sample.filename}: {e}")
                # Při chybě hash výpočtu přidej do samples_to_analyze bez hash
                samples_to_analyze.append(sample)

        logger.info(f"Cache analysis complete: {len(cached_samples)} cached, {len(samples_to_analyze)} to analyze")

        # Ulož session pokud byly nějaké změny
        self._save_session()

        return cached_samples, samples_to_analyze

    def _validate_cached_data(self, cached_data: dict, filename: str) -> bool:
        """NOVÁ METODA: Validuje zda cached data obsahují potřebné informace."""
        required_keys = ['filename', 'analyzed_timestamp']

        for key in required_keys:
            if key not in cached_data:
                logger.warning(f"Missing key '{key}' in cached data for {filename}")
                return False

        # Kontroluj zda jsou pitch nebo amplitude data přítomny
        has_pitch = cached_data.get('detected_midi') is not None
        has_amplitude = cached_data.get('velocity_amplitude') is not None

        if not has_pitch and not has_amplitude:
            logger.warning(f"No analysis data in cache for {filename}")
            return False

        return True

    def _restore_sample_from_cache(self, sample: SampleMetadata, cached_data: dict, file_hash: str):
        """NOVÁ METODA: Obnoví sample data z cache."""
        # Pitch detection data
        sample.detected_midi = cached_data.get("detected_midi")
        sample.detected_frequency = cached_data.get("detected_frequency")
        sample.pitch_confidence = cached_data.get("pitch_confidence", 0.0)
        sample.pitch_method = cached_data.get("pitch_method", "cached")

        # Amplitude analysis data
        sample.velocity_amplitude = cached_data.get("velocity_amplitude")
        sample.velocity_amplitude_db = cached_data.get("velocity_amplitude_db")
        sample.velocity_duration_ms = cached_data.get("velocity_duration_ms")

        # Legacy amplitude data pro kompatibilitu
        sample.peak_amplitude = cached_data.get("peak_amplitude")
        sample.peak_amplitude_db = cached_data.get("peak_amplitude_db")
        sample.rms_amplitude = cached_data.get("rms_amplitude")
        sample.rms_amplitude_db = cached_data.get("rms_amplitude_db")
        sample.peak_position = cached_data.get("peak_position")
        sample.peak_position_seconds = cached_data.get("peak_position_seconds")

        # Attack envelope data
        sample.attack_peak = cached_data.get("attack_peak")
        sample.attack_time = cached_data.get("attack_time")
        sample.attack_slope = cached_data.get("attack_slope")

        # Audio info
        sample.duration = cached_data.get("duration")
        sample.sample_rate = cached_data.get("sample_rate")
        sample.channels = cached_data.get("channels")

        # Status flags
        sample.analyzed = True
        sample._hash = file_hash

        logger.debug(f"Restored from cache: {sample.filename} - MIDI: {sample.detected_midi}, RMS: {sample.velocity_amplitude}")

    def cache_analyzed_samples(self, samples: List[SampleMetadata]):
        """
        ROZŠÍŘENÁ METODA: Uloží analyzované samples do cache.

        Args:
            samples: Seznam analyzovaných samples
        """
        if not self.session_data:
            logger.warning("No session data available for caching samples")
            return

        logger.info(f"Starting to cache {len(samples)} samples...")
        cached_count = 0
        skipped_count = 0

        for sample in samples:
            # Debug info
            has_hash = hasattr(sample, '_hash')
            is_analyzed = sample.analyzed
            logger.debug(f"Processing sample {sample.filename}: has_hash={has_hash}, analyzed={is_analyzed}")

            if hasattr(sample, '_hash') and sample.analyzed:
                file_hash = sample._hash

                # ROZŠÍŘENÉ cache entry s více daty - OPRAVA: převod numpy typů
                cache_entry = {
                    # Basic file info
                    "filename": sample.filename,
                    "file_path": str(sample.filepath),
                    "file_size": sample.filepath.stat().st_size if sample.filepath.exists() else 0,

                    # Pitch detection results - převod na Python typy
                    "detected_midi": int(sample.detected_midi) if sample.detected_midi is not None else None,
                    "detected_frequency": float(sample.detected_frequency) if sample.detected_frequency is not None else None,
                    "pitch_confidence": float(sample.pitch_confidence) if sample.pitch_confidence is not None else None,
                    "pitch_method": str(sample.pitch_method) if sample.pitch_method else None,

                    # Amplitude analysis results (primary) - převod na Python typy
                    "velocity_amplitude": float(sample.velocity_amplitude) if sample.velocity_amplitude is not None else None,
                    "velocity_amplitude_db": float(sample.velocity_amplitude_db) if sample.velocity_amplitude_db is not None else None,
                    "velocity_duration_ms": float(sample.velocity_duration_ms) if sample.velocity_duration_ms is not None else None,

                    # Legacy amplitude data - převod na Python typy
                    "peak_amplitude": float(getattr(sample, 'peak_amplitude')) if getattr(sample, 'peak_amplitude', None) is not None else None,
                    "peak_amplitude_db": float(getattr(sample, 'peak_amplitude_db')) if getattr(sample, 'peak_amplitude_db', None) is not None else None,
                    "rms_amplitude": float(getattr(sample, 'rms_amplitude')) if getattr(sample, 'rms_amplitude', None) is not None else None,
                    "rms_amplitude_db": float(getattr(sample, 'rms_amplitude_db')) if getattr(sample, 'rms_amplitude_db', None) is not None else None,
                    "peak_position": int(getattr(sample, 'peak_position')) if getattr(sample, 'peak_position', None) is not None else None,
                    "peak_position_seconds": float(getattr(sample, 'peak_position_seconds')) if getattr(sample, 'peak_position_seconds', None) is not None else None,

                    # Attack envelope data - převod na Python typy
                    "attack_peak": float(getattr(sample, 'attack_peak')) if getattr(sample, 'attack_peak', None) is not None else None,
                    "attack_time": float(getattr(sample, 'attack_time')) if getattr(sample, 'attack_time', None) is not None else None,
                    "attack_slope": float(getattr(sample, 'attack_slope')) if getattr(sample, 'attack_slope', None) is not None else None,

                    # Audio properties - převod na Python typy
                    "duration": float(sample.duration) if sample.duration is not None else None,
                    "sample_rate": int(sample.sample_rate) if sample.sample_rate is not None else None,
                    "channels": int(sample.channels) if sample.channels is not None else None,

                    # Cache metadata
                    "analyzed_timestamp": datetime.now().isoformat(),
                    "cache_version": "2.0"  # Pro budoucí kompatibilitu
                }

                self.session_data["samples_cache"][file_hash] = cache_entry
                cached_count += 1
                logger.debug(f"✓ Cached: {sample.filename} with hash {file_hash[:8]}... "
                           f"MIDI: {sample.detected_midi}, RMS: {sample.velocity_amplitude}")
            else:
                reason = "missing _hash" if not hasattr(sample, '_hash') else "not analyzed"
                logger.warning(f"✗ Skipped {sample.filename}: {reason}")
                skipped_count += 1

        if cached_count > 0:
            # EXPLICITNÍ ULOŽENÍ
            logger.info(f"Saving session with {cached_count} new cache entries...")
            self._save_session()

            # Verifikace uložení
            if self.current_session:
                session_file = self._get_session_file(self.current_session)
                if session_file.exists():
                    try:
                        # Načti a zkontroluj uložená data
                        with open(session_file, 'r', encoding='utf-8') as f:
                            saved_data = json.load(f)

                        saved_cache_count = len(saved_data.get("samples_cache", {}))
                        logger.info(f"✓ Session file verification: {saved_cache_count} cache entries found in file")

                        # Debug: výpis prvních pár cache keys
                        cache_keys = list(saved_data.get("samples_cache", {}).keys())[:3]
                        if cache_keys:
                            logger.debug(f"Sample cache keys: {[key[:8] + '...' for key in cache_keys]}")

                    except Exception as e:
                        logger.error(f"Failed to verify saved session file: {e}")
                else:
                    logger.error(f"Session file doesn't exist after save: {session_file}")

            logger.info(f"Successfully cached {cached_count} samples, skipped {skipped_count}")
        else:
            logger.error(f"No samples were cached! All {len(samples)} samples were skipped. "
                        f"Reasons: missing _hash attribute or not analyzed")

            # Debug: Výpis proč se samples nečachují
            for i, sample in enumerate(samples[:5]):  # Prvních 5 pro debug
                has_hash = hasattr(sample, '_hash')
                is_analyzed = sample.analyzed
                logger.debug(f"Sample {i}: {sample.filename} - hash: {has_hash}, analyzed: {is_analyzed}")
                if has_hash:
                    logger.debug(f"  Hash: {sample._hash[:8]}...")
                if sample.detected_midi:
                    logger.debug(f"  MIDI: {sample.detected_midi}")
                if sample.velocity_amplitude:
                    logger.debug(f"  RMS: {sample.velocity_amplitude:.6f}")

    def update_sample_pitch(self, sample: SampleMetadata, old_midi: int, new_midi: int):
        """
        NOVÁ METODA: Aktualizuje MIDI notu sample v cache při transpozici.

        Args:
            sample: Sample který byl transponován
            old_midi: Původní MIDI nota
            new_midi: Nová MIDI nota
        """
        if not self.session_data or not hasattr(sample, '_hash'):
            logger.warning(f"Cannot update pitch for {sample.filename} - no session data or hash")
            return

        file_hash = sample._hash

        if file_hash in self.session_data["samples_cache"]:
            # Aktualizuj cached data s bezpečnou konverzí typů
            cache_entry = self.session_data["samples_cache"][file_hash]
            cache_entry["detected_midi"] = int(new_midi) if new_midi is not None else None

            # Přepočítej frekvenci na základě nové MIDI noty
            if new_midi is not None:
                new_frequency = 440.0 * (2 ** ((new_midi - 69) / 12))
                cache_entry["detected_frequency"] = float(new_frequency)

            # Uprav timestamp
            cache_entry["last_modified"] = datetime.now().isoformat()
            cache_entry["pitch_method"] = cache_entry.get("pitch_method", "cached") + "_modified"

            self._save_session()
            logger.info(f"Updated pitch in cache: {sample.filename} MIDI {old_midi} -> {new_midi}")
        else:
            logger.warning(f"Sample {sample.filename} not found in cache, cannot update pitch")

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
        mapped_count = 0

        for (midi, velocity), sample in mapping.items():
            if hasattr(sample, '_hash'):
                key = f"{midi},{velocity}"
                session_mapping[key] = sample._hash
                mapped_count += 1
            else:
                logger.warning(f"Sample {sample.filename} has no hash, calculating it now...")
                try:
                    # Pokus o výpočet hash na místě
                    file_hash = self._calculate_file_hash(sample.filepath)
                    sample._hash = file_hash
                    key = f"{midi},{velocity}"
                    session_mapping[key] = file_hash
                    mapped_count += 1
                except Exception as e:
                    logger.error(f"Failed to calculate hash for mapping save: {sample.filename}: {e}")

        self.session_data["mapping"] = session_mapping
        self._save_session()
        logger.info(f"Saved mapping: {mapped_count} entries")

    def restore_mapping(self, all_samples: List[SampleMetadata]) -> Dict[Tuple[int, int], SampleMetadata]:
        """
        Obnoví mapping ze session.

        Args:
            all_samples: Všechny dostupné samples

        Returns:
            Dictionary (midi, velocity) -> SampleMetadata
        """
        if not self.session_data or not self.session_data.get("mapping"):
            logger.info("No mapping data in session to restore")
            return {}

        # Vytvoř hash->sample lookup
        hash_to_sample = {}
        for sample in all_samples:
            if hasattr(sample, '_hash'):
                hash_to_sample[sample._hash] = sample
            else:
                # Pokud sample nemá hash, zkus ho spočítat
                try:
                    file_hash = self._calculate_file_hash(sample.filepath)
                    sample._hash = file_hash
                    hash_to_sample[file_hash] = sample
                except Exception as e:
                    logger.warning(f"Cannot calculate hash for {sample.filename}: {e}")

        # Restore mapping
        restored_mapping = {}
        session_mapping = self.session_data["mapping"]
        restored_count = 0

        for key, file_hash in session_mapping.items():
            try:
                midi_str, velocity_str = key.split(',')
                midi = int(midi_str)
                velocity = int(velocity_str)

                if file_hash in hash_to_sample:
                    sample = hash_to_sample[file_hash]
                    sample.mapped = True
                    restored_mapping[(midi, velocity)] = sample
                    restored_count += 1
                    logger.debug(f"Restored mapping: {sample.filename} -> MIDI {midi}, V{velocity}")
                else:
                    logger.warning(f"Sample with hash {file_hash[:8]}... not found for mapping {key}")

            except Exception as e:
                logger.error(f"Failed to restore mapping entry {key}: {e}")

        logger.info(f"Restored mapping: {restored_count}/{len(session_mapping)} entries")
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

    def get_cache_stats(self) -> Dict:
        """NOVÁ METODA: Vrátí statistiky cache."""
        if not self.session_data:
            return {"total_cached": 0, "cache_size_mb": 0}

        cache_size = len(json.dumps(self.session_data.get("samples_cache", {})))

        return {
            "total_cached": len(self.session_data.get("samples_cache", {})),
            "cache_size_mb": cache_size / (1024 * 1024),
            "mapping_entries": len(self.session_data.get("mapping", {}))
        }

    def cleanup_cache(self, valid_file_paths: List[Path]) -> int:
        """
        NOVÁ METODA: Vyčistí cache od souborů které už neexistují.

        Args:
            valid_file_paths: Seznam existujících souborů

        Returns:
            Počet odstraněných cache entries
        """
        if not self.session_data or not self.session_data.get("samples_cache"):
            return 0

        # Vytvoř set validních path stringů
        valid_paths = {str(path) for path in valid_file_paths}

        # Najdi cache entries pro neexistující soubory
        to_remove = []
        for file_hash, cache_entry in self.session_data["samples_cache"].items():
            file_path = cache_entry.get("file_path")
            if file_path and file_path not in valid_paths:
                to_remove.append(file_hash)

        # Odstraň neplatné entries
        removed_count = 0
        for file_hash in to_remove:
            del self.session_data["samples_cache"][file_hash]
            removed_count += 1

        if removed_count > 0:
            self._save_session()
            logger.info(f"Cleaned up {removed_count} invalid cache entries")

        return removed_count

    def _get_session_file(self, session_name: str) -> Path:
        """Vrátí cestu k session souboru."""
        return self.sessions_folder / f"session-{session_name}.json"

    def calculate_file_hash(self, file_path: Path) -> str:
        """
        VEŘEJNÁ METODA pro kompatibilitu: Spočítá MD5 hash celého souboru.

        Args:
            file_path: Cesta k souboru

        Returns:
            MD5 hash jako hexadecimální string
        """
        return self._calculate_file_hash(file_path)

    def set_cache(self, file_hash: str, cached_data: dict):
        """
        KOMPATIBILNÍ METODA: Uloží data do cache pod daným hashem.

        Args:
            file_hash: MD5 hash souboru
            cached_data: Data k uložení
        """
        if not self.session_data:
            logger.warning("No session data available for caching")
            return

        self.session_data["samples_cache"][file_hash] = cached_data
        # Auto-save po každém cache zápisu není nutný, uložíme při zavírání

    def _calculate_file_hash(self, file_path: Path) -> str:
        """VYLEPŠENÁ METODA: Spočítá MD5 hash celého souboru s lepším error handlingem."""
        if not file_path.exists():
            raise FileNotFoundError(f"File does not exist: {file_path}")

        hash_md5 = hashlib.md5()

        try:
            with open(file_path, "rb") as f:
                # Čtení po blocích pro úsporu paměti
                while chunk := f.read(8192):
                    hash_md5.update(chunk)

            file_hash = hash_md5.hexdigest()
            logger.debug(f"Calculated hash for {file_path.name}: {file_hash}")
            return file_hash

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
            # Backup existující soubor
            if session_file.exists():
                backup_file = session_file.with_suffix('.json.backup')
                session_file.replace(backup_file)

            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(self.session_data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Session saved: {session_file}")

        except Exception as e:
            logger.error(f"Failed to save session {self.current_session}: {e}")

            # Pokus o obnovení z backup
            backup_file = session_file.with_suffix('.json.backup')
            if backup_file.exists():
                backup_file.replace(session_file)
                logger.info("Restored session from backup after save failure")

    def close_session(self):
        """Zavře aktuální session."""
        if self.session_data:
            self._save_session()

        self.current_session = None
        self.session_data = None
        logger.info("Session closed")