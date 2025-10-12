"""
export_thread.py - Worker thread pro asynchronní export s progress barem
"""

import logging
from typing import Dict, Tuple
from pathlib import Path
from PySide6.QtCore import QThread, Signal

from models import SampleMetadata
from export_utils import ExportManager, ExportValidator
from midi_utils import MidiUtils

logger = logging.getLogger(__name__)


class ExportThread(QThread):
    """Worker thread pro asynchronní export samples s progress barem."""

    progress_updated = Signal(int, str)  # progress percentage, message
    export_completed = Signal(dict)  # export_info dictionary
    export_failed = Signal(str)  # error message

    def __init__(self, mapping: Dict[Tuple[int, int], SampleMetadata], output_folder: Path, session_manager=None):
        super().__init__()
        self.mapping = mapping
        self.output_folder = output_folder
        self.session_manager = session_manager
        self.export_manager = None
        self._is_cancelled = False

    def run(self):
        """Spustí asynchronní export."""
        try:
            logger.info(f"Starting export thread with {len(self.mapping)} samples")

            # Inicializace
            self.progress_updated.emit(0, "Příprava exportu...")
            self.export_manager = ExportManager(self.output_folder)

            # Validace před exportem
            self.progress_updated.emit(5, "Validace samples...")
            errors = ExportValidator.validate_mapping(self.mapping)
            if errors:
                error_msg = f"Chyby při validaci:\n" + "\n".join(errors[:5])
                self.export_failed.emit(error_msg)
                return

            if self._is_cancelled:
                return

            # Validace výstupní složky
            self.progress_updated.emit(10, "Kontrola výstupní složky...")
            if not self.export_manager.validate_export_folder():
                self.export_failed.emit("Výstupní složka není dostupná pro zápis")
                return

            # Export jednotlivých samples
            self.progress_updated.emit(15, "Zahajuji export samples...")
            export_info = self._export_with_progress()

            if self._is_cancelled:
                return

            # Export instrument-definition.json
            if self.session_manager:
                try:
                    self.progress_updated.emit(95, "Vytvářím instrument-definition.json...")

                    # Získej metadata ze session manageru
                    metadata = self.session_manager.get_metadata()

                    # Přidej velocity_layers do metadata pro export
                    if metadata:
                        metadata['velocity_layers'] = self.session_manager.get_velocity_layers()

                    # Exportuj JSON soubor
                    json_path = self.export_manager.export_instrument_definition(metadata, self.mapping)
                    export_info['instrument_definition_path'] = str(json_path)

                    # Inkrementuj verzi nástroje po úspěšném exportu
                    new_version = self.session_manager.increment_instrument_version()
                    logger.info(f"Instrument version incremented to: {new_version}")

                except Exception as e:
                    logger.error(f"Failed to export instrument definition: {e}")
                    # Neukončuj export kvůli chybě v JSON - pouze loguj
                    export_info['instrument_definition_error'] = str(e)

            # Dokončení
            self.progress_updated.emit(100, f"Export dokončen: {export_info['exported_count']} samples")
            self.export_completed.emit(export_info)

        except Exception as e:
            logger.error(f"Export thread failed: {e}", exc_info=True)
            self.export_failed.emit(f"Chyba při exportu: {e}")

    def _export_with_progress(self) -> dict:
        """Provede export s detailním progress reportingem."""
        total_samples = len(self.mapping)
        total_files = total_samples * 2  # 2 formáty (44kHz, 48kHz) pro každý sample

        export_info = {
            'exported_count': 0,
            'failed_count': 0,
            'exported_files': [],
            'failed_files': [],
            'total_files': 0
        }

        base_progress = 15  # Pokračujeme od 15%
        export_progress_range = 80  # 15% až 95%

        current_sample = 0

        for key, sample in self.mapping.items():
            if self._is_cancelled:
                return export_info

            midi_note, velocity = key
            current_sample += 1

            # Progress calculation
            progress_percent = base_progress + int((current_sample / total_samples) * export_progress_range)

            try:
                # Status zpráva
                note_name = MidiUtils.midi_to_note_name(midi_note)
                status_msg = f"Exportuji: {sample.filename} → {note_name} (MIDI {midi_note}, V{velocity}) [{current_sample}/{total_samples}]"
                self.progress_updated.emit(progress_percent, status_msg)

                # Validace jednotlivého sample
                if not self.export_manager._validate_single_sample(sample, midi_note, velocity):
                    export_info['failed_files'].append((sample.filename, "Sample neprošel validací"))
                    export_info['failed_count'] += 1
                    continue

                # Export sample do obou formátů
                exported_files = self.export_manager._export_single_sample(sample, midi_note, velocity)
                export_info['exported_files'].extend(exported_files)
                export_info['exported_count'] += 1

                logger.info(
                    f"✓ Exported: {sample.filename} -> MIDI {midi_note}, V{velocity} ({len(exported_files)} files)")

            except Exception as e:
                logger.error(f"Failed to export {sample.filename}: {e}")
                export_info['failed_files'].append((sample.filename, str(e)))
                export_info['failed_count'] += 1

        export_info['total_files'] = len(export_info['exported_files'])
        return export_info

    def cancel_export(self):
        """Zruší probíhající export."""
        self._is_cancelled = True
        logger.info("Export cancellation requested")
        self.progress_updated.emit(0, "Rušení exportu...")