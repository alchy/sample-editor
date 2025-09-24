"""
export_utils.py - Utility funkce pro export samples - OPRAVENÁ VERZE
"""

import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
import logging

from models import SampleMetadata
from midi_utils import MidiUtils

logger = logging.getLogger(__name__)


class ExportManager:
    """Správce exportu namapovaných samples - OPRAVENÁ VERZE."""

    def __init__(self, output_folder: Path):
        self.output_folder = Path(output_folder)
        self.export_formats = [
            (44100, 'f44'),
            (48000, 'f48')
        ]

    def export_mapped_samples(self, mapping: Dict[Tuple[int, int], SampleMetadata]) -> Dict[str, Union[int, List[str], List[Tuple[str, str]]]]:
        """
        Exportuje všechny namapované samples.

        Args:
            mapping: Dictionary (midi_note, velocity) -> SampleMetadata

        Returns:
            Dictionary s informacemi o exportu
        """
        if not mapping:
            raise ValueError("Žádné samples k exportu")

        # OPRAVA: Validace před exportem
        validation_errors = ExportValidator.validate_mapping(mapping)
        if validation_errors:
            raise ValueError(f"Validační chyby: {'; '.join(validation_errors[:3])}")

        # Vytvoř výstupní složku pokud neexistuje
        try:
            self.output_folder.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(f"Nelze vytvořit výstupní složku: {e}")

        export_info = {
            'exported_count': 0,
            'failed_count': 0,
            'exported_files': [],
            'failed_files': [],
            'total_files': 0
        }

        # OPRAVA: Bezpečná iterace přes mapping
        for key, sample in list(mapping.items()):
            if not isinstance(key, tuple) or len(key) != 2:
                logger.error(f"Neplatný klíč v mapping: {key}")
                export_info['failed_files'].append((str(key), "Neplatný formát klíče"))
                export_info['failed_count'] += 1
                continue

            midi_note, velocity = key

            try:
                # OPRAVA: Dodatečná validace sample
                if not self._validate_single_sample(sample, midi_note, velocity):
                    export_info['failed_files'].append((sample.filename, "Sample neprošel validací"))
                    export_info['failed_count'] += 1
                    continue

                exported_files = self._export_single_sample(sample, midi_note, velocity)
                export_info['exported_files'].extend(exported_files)
                export_info['exported_count'] += 1

                logger.info(f"✓ Exportován: {sample.filename} -> MIDI {midi_note}, V{velocity}")

            except Exception as e:
                logger.error(f"Chyba při exportu {sample.filename}: {e}")
                export_info['failed_files'].append((sample.filename, str(e)))
                export_info['failed_count'] += 1

        export_info['total_files'] = len(export_info['exported_files'])

        logger.info(f"Export dokončen: {export_info['exported_count']} úspěšných, "
                    f"{export_info['failed_count']} chybných")

        return export_info

    def _validate_single_sample(self, sample: SampleMetadata, midi_note: int, velocity: int) -> bool:
        """Validuje jednotlivý sample před exportem."""
        if not sample:
            return False

        if not isinstance(sample, SampleMetadata):
            logger.error(f"Sample není instance SampleMetadata: {type(sample)}")
            return False

        if not sample.filepath or not sample.filepath.exists():
            logger.error(f"Soubor neexistuje: {sample.filepath}")
            return False

        if not MidiUtils.is_piano_range(midi_note):
            logger.error(f"MIDI nota {midi_note} není v piano rozsahu")
            return False

        if not (0 <= velocity <= 7):
            logger.error(f"Velocity {velocity} není v rozsahu 0-7")
            return False

        return True

    def _export_single_sample(self, sample: SampleMetadata, midi_note: int, velocity: int) -> List[Path]:
        """
        Exportuje jeden sample do všech formátů.

        Returns:
            Seznam cest k exportovaným souborům
        """
        exported_files = []

        for sample_rate, sr_suffix in self.export_formats:
            try:
                output_filename = MidiUtils.generate_filename(midi_note, velocity, sample_rate)
                output_path = self.output_folder / output_filename

                # OPRAVA: Kontrola existence zdrojového souboru
                if not sample.filepath.exists():
                    raise FileNotFoundError(f"Zdrojový soubor neexistuje: {sample.filepath}")

                # OPRAVA: Bezpečné kopírování s error handlingem
                try:
                    # Pro prototyp - jen kopírování
                    # V budoucnu zde bude sample rate konverze a případná pitch korekce
                    shutil.copy2(sample.filepath, output_path)

                    # OPRAVA: Verifikace úspěšného kopírování
                    if not output_path.exists():
                        raise RuntimeError(f"Kopírování selhalo - výstupní soubor neexistuje")

                    # OPRAVA: Kontrola velikosti souboru
                    if output_path.stat().st_size == 0:
                        raise RuntimeError(f"Výstupní soubor je prázdný")

                    exported_files.append(output_path)
                    logger.debug(f"Exportován: {output_filename}")

                except (OSError, IOError) as e:
                    raise RuntimeError(f"Chyba při kopírování souboru: {e}")

            except Exception as e:
                logger.error(f"Chyba při exportu do {sr_suffix}: {e}")
                # Continue with other formats even if one fails
                continue

        if not exported_files:
            raise RuntimeError("Nepodařilo se exportovat žádný formát")

        return exported_files

    def validate_export_folder(self) -> bool:
        """Ověří, zda je výstupní složka dostupná pro zápis."""
        try:
            self.output_folder.mkdir(parents=True, exist_ok=True)

            # Test zápisu
            test_file = self.output_folder / "test_write.tmp"
            test_file.write_text("test")
            test_file.unlink()

            return True

        except Exception as e:
            logger.error(f"Výstupní složka není dostupná pro zápis: {e}")
            return False

    def get_export_preview(self, mapping: Dict[Tuple[int, int], SampleMetadata]) -> List[Dict]:
        """
        Vrátí náhled toho, co bude exportováno.

        Returns:
            Seznam dictionary s informacemi o jednotlivých exportech
        """
        preview = []

        # OPRAVA: Bezpečná iterace přes mapping
        for key, sample in mapping.items():
            if not isinstance(key, tuple) or len(key) != 2:
                continue

            midi_note, velocity = key

            if not self._validate_single_sample(sample, midi_note, velocity):
                continue

            try:
                note_name = MidiUtils.midi_to_note_name(midi_note)

                for sample_rate, sr_suffix in self.export_formats:
                    filename = MidiUtils.generate_filename(midi_note, velocity, sample_rate)

                    preview.append({
                        'source_file': sample.filename,
                        'output_file': filename,
                        'midi_note': midi_note,
                        'note_name': note_name,
                        'velocity': velocity,
                        'sample_rate': sample_rate,
                        'output_path': self.output_folder / filename,
                        'valid': True
                    })
            except Exception as e:
                logger.error(f"Chyba při vytváření preview pro {sample.filename}: {e}")
                preview.append({
                    'source_file': sample.filename,
                    'output_file': 'ERROR',
                    'midi_note': midi_note,
                    'note_name': 'ERROR',
                    'velocity': velocity,
                    'sample_rate': 0,
                    'output_path': None,
                    'valid': False,
                    'error': str(e)
                })

        return preview

    def cleanup_previous_exports(self, pattern: str = "m*-vel*-f*.wav") -> int:
        """
        Vyčistí předchozí exporty podle pattern.

        Returns:
            Počet smazaných souborů
        """
        deleted_count = 0

        try:
            for file_path in self.output_folder.glob(pattern):
                if file_path.is_file():
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"Smazán starý export: {file_path.name}")
                    except Exception as e:
                        logger.warning(f"Nelze smazat {file_path.name}: {e}")

            logger.info(f"Vyčištěno {deleted_count} starých exportů")

        except Exception as e:
            logger.error(f"Chyba při čištění starých exportů: {e}")

        return deleted_count


class ExportValidator:
    """Validátor pro export operace - OPRAVENÁ VERZE."""

    @staticmethod
    def validate_mapping(mapping: Dict[Tuple[int, int], SampleMetadata]) -> List[str]:
        """
        Validuje mapování před exportem.

        Returns:
            Seznam chybových zpráv (prázdný seznam = OK)
        """
        errors = []

        if not mapping:
            errors.append("Žádné samples nejsou namapované")
            return errors

        if not isinstance(mapping, dict):
            errors.append("Mapping není dictionary")
            return errors

        for key, sample in mapping.items():
            try:
                # OPRAVA: Validace klíče
                if not isinstance(key, tuple) or len(key) != 2:
                    errors.append(f"Neplatný klíč v mapping: {key}")
                    continue

                midi_note, velocity = key

                # Validace MIDI rozsahu
                if not isinstance(midi_note, int) or not MidiUtils.is_piano_range(midi_note):
                    errors.append(f"MIDI nota {midi_note} není v piano rozsahu")

                # Validace velocity
                if not isinstance(velocity, int) or not (0 <= velocity <= 7):
                    errors.append(f"Velocity {velocity} není v rozsahu 0-7")

                # OPRAVA: Validace sample objektu
                if not isinstance(sample, SampleMetadata):
                    errors.append(f"Sample pro MIDI {midi_note}, V{velocity} není SampleMetadata instance")
                    continue

                # Validace existence souboru
                if not sample.filepath or not sample.filepath.exists():
                    errors.append(f"Soubor {sample.filename} neexistuje")

                # Validace analýzy
                if not sample.analyzed:
                    errors.append(f"Sample {sample.filename} nebyl analyzován")

            except Exception as e:
                errors.append(f"Chyba při validaci: {e}")

        return errors

    @staticmethod
    def check_filename_conflicts(mapping: Dict[Tuple[int, int], SampleMetadata]) -> List[str]:
        """
        Zkontroluje konflikty v názvech výstupních souborů.

        Returns:
            Seznam konfliktů
        """
        conflicts = []
        filename_map = {}

        for key, sample in mapping.items():
            if not isinstance(key, tuple) or len(key) != 2:
                continue

            midi_note, velocity = key

            try:
                for sample_rate, sr_suffix in [(44100, 'f44'), (48000, 'f48')]:
                    filename = MidiUtils.generate_filename(midi_note, velocity, sample_rate)

                    if filename in filename_map:
                        conflicts.append(
                            f"Konflikt názvu '{filename}': "
                            f"{filename_map[filename].filename} vs {sample.filename}"
                        )
                    else:
                        filename_map[filename] = sample
            except Exception as e:
                conflicts.append(f"Chyba při kontrole konfliktů pro {sample.filename}: {e}")

        return conflicts

    @staticmethod
    def validate_export_folder(output_folder: Path) -> List[str]:
        """
        Validuje výstupní složku.

        Returns:
            Seznam chyb (prázdný = OK)
        """
        errors = []

        try:
            if not output_folder:
                errors.append("Výstupní složka není nastavena")
                return errors

            output_folder = Path(output_folder)

            # Pokus o vytvoření složky
            try:
                output_folder.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Nelze vytvořit výstupní složku: {e}")
                return errors

            # Test zápisu
            try:
                test_file = output_folder / "test_write.tmp"
                test_file.write_text("test")
                test_file.unlink()
            except Exception as e:
                errors.append(f"Nelze zapisovat do výstupní složky: {e}")

        except Exception as e:
            errors.append(f"Chyba při validaci výstupní složky: {e}")

        return errors