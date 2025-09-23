"""
export_utils.py - Utility funkce pro export sampleů
"""

import shutil
from pathlib import Path
from typing import Dict, List, Tuple
import logging

from models import SampleMetadata
from midi_utils import MidiUtils

logger = logging.getLogger(__name__)


class ExportManager:
    """Správce exportu namapovaných sampleů"""

    def __init__(self, output_folder: Path):
        self.output_folder = Path(output_folder)
        self.export_formats = [
            (44100, 'f44'),
            (48000, 'f48')
        ]

    def export_mapped_samples(self, mapping: Dict[Tuple[int, int], SampleMetadata]) -> Dict:
        """
        Exportuje všechny namapované samples

        Args:
            mapping: Dictionary (midi_note, velocity) -> SampleMetadata

        Returns:
            Dictionary s informacemi o exportu
        """
        if not mapping:
            raise ValueError("Žádné samples k exportu")

        # Vytvoř výstupní složku pokud neexistuje
        self.output_folder.mkdir(parents=True, exist_ok=True)

        export_info = {
            'exported_count': 0,
            'failed_count': 0,
            'exported_files': [],
            'failed_files': [],
            'total_files': 0
        }

        for (midi_note, velocity), sample in mapping.items():
            try:
                exported_files = self._export_single_sample(sample, midi_note, velocity)
                export_info['exported_files'].extend(exported_files)
                export_info['exported_count'] += 1

            except Exception as e:
                logger.error(f"Chyba při exportu {sample.filename}: {e}")
                export_info['failed_files'].append((sample.filename, str(e)))
                export_info['failed_count'] += 1

        export_info['total_files'] = len(export_info['exported_files'])

        logger.info(f"Export dokončen: {export_info['exported_count']} úspěšných, "
                    f"{export_info['failed_count']} chybných")

        return export_info

    def _export_single_sample(self, sample: SampleMetadata, midi_note: int, velocity: int) -> List[Path]:
        """
        Exportuje jeden sample do všech formátů

        Returns:
            Seznam cest k exportovaným souborům
        """
        exported_files = []

        for sample_rate, sr_suffix in self.export_formats:
            output_filename = MidiUtils.generate_filename(midi_note, velocity, sample_rate)
            output_path = self.output_folder / output_filename

            # Pro prototyp - jen kopírování
            # V budoucnu zde bude sample rate konverze a případná pitch korekce
            shutil.copy2(sample.filepath, output_path)

            exported_files.append(output_path)
            logger.debug(f"Exportován: {output_filename}")

        return exported_files

    def validate_export_folder(self) -> bool:
        """Ověří, zda je výstupní složka dostupná pro zápis"""
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
        Vrátí náhled toho, co bude exportováno

        Returns:
            Seznam dictonary s informacemi o jednotlivých exportech
        """
        preview = []

        for (midi_note, velocity), sample in mapping.items():
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
                    'output_path': self.output_folder / filename
                })

        return preview

    def cleanup_previous_exports(self, pattern: str = "m*-vel*-f*.wav") -> int:
        """
        Vyčistí předchozí exporty podle pattern

        Returns:
            Počet smazaných souborů
        """
        deleted_count = 0

        try:
            for file_path in self.output_folder.glob(pattern):
                if file_path.is_file():
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Smazán starý export: {file_path.name}")

            logger.info(f"Vyčištěno {deleted_count} starých exportů")

        except Exception as e:
            logger.error(f"Chyba při čištění starých exportů: {e}")

        return deleted_count


class ExportValidator:
    """Validátor pro export operace"""

    @staticmethod
    def validate_mapping(mapping: Dict[Tuple[int, int], SampleMetadata]) -> List[str]:
        """
        Validuje mapování před exportem

        Returns:
            Seznam chybových zpráv (prázdný seznam = OK)
        """
        errors = []

        if not mapping:
            errors.append("Žádné samples nejsou namapované")
            return errors

        for (midi_note, velocity), sample in mapping.items():
            # Validace MIDI rozsahu
            if not MidiUtils.is_piano_range(midi_note):
                errors.append(f"MIDI nota {midi_note} není v piano rozsahu")

            # Validace velocity
            if not (0 <= velocity <= 7):
                errors.append(f"Velocity {velocity} není v platném rozsahu 0-7")

            # Validace existence souboru
            if not sample.filepath.exists():
                errors.append(f"Soubor {sample.filename} neexistuje")

            # Validace analýzy
            if not sample.analyzed:
                errors.append(f"Sample {sample.filename} nebyl analyzován")

        return errors

    @staticmethod
    def check_filename_conflicts(mapping: Dict[Tuple[int, int], SampleMetadata]) -> List[str]:
        """
        Zkontroluje konflikty v názvech výstupních souborů

        Returns:
            Seznam konfliktů
        """
        conflicts = []
        filename_map = {}

        for (midi_note, velocity), sample in mapping.items():
            for sample_rate, sr_suffix in [(44100, 'f44'), (48000, 'f48')]:
                filename = MidiUtils.generate_filename(midi_note, velocity, sample_rate)

                if filename in filename_map:
                    conflicts.append(
                        f"Konflikt názvu '{filename}': "
                        f"{filename_map[filename].filename} vs {sample.filename}"
                    )
                else:
                    filename_map[filename] = sample

        return conflicts