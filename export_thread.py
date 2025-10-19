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

            # Export samples-report.txt
            if self.session_manager:
                try:
                    self.progress_updated.emit(97, "Creating samples-report.txt...")

                    velocity_layers = self.session_manager.get_velocity_layers()
                    report_path = self._generate_samples_report(velocity_layers)
                    export_info['samples_report_path'] = str(report_path)
                    logger.info(f"Samples report created: {report_path}")

                except Exception as e:
                    logger.error(f"Failed to create samples report: {e}")
                    export_info['samples_report_error'] = str(e)

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

    def _generate_samples_report(self, velocity_layers: int) -> Path:
        """
        Generate samples-report.txt with coverage analysis.
        Shows assigned samples count and missing notes sorted by gap count.
        Analyzes only the actual range of notes that have samples assigned.
        """
        from collections import defaultdict

        # Determine actual MIDI range from mapped samples
        if not self.mapping:
            # No samples mapped - use full piano range as fallback
            actual_min_midi = 21
            actual_max_midi = 108
        else:
            mapped_midis = [key[0] for key in self.mapping.keys()]
            actual_min_midi = min(mapped_midis)
            actual_max_midi = max(mapped_midis)

        # Analyze coverage for each MIDI note in the actual range
        coverage = defaultdict(lambda: {'assigned': 0, 'missing': 0, 'layers': []})

        for midi_note in range(actual_min_midi, actual_max_midi + 1):
            for velocity in range(velocity_layers):
                key = (midi_note, velocity)
                if key in self.mapping:
                    coverage[midi_note]['assigned'] += 1
                    coverage[midi_note]['layers'].append(velocity)
                else:
                    coverage[midi_note]['missing'] += 1

        # Calculate statistics
        total_notes = actual_max_midi - actual_min_midi + 1
        total_possible_samples = total_notes * velocity_layers
        total_assigned = sum(c['assigned'] for c in coverage.values())
        total_missing = total_possible_samples - total_assigned

        # Find notes with missing samples
        notes_with_gaps = []
        for midi_note in range(actual_min_midi, actual_max_midi + 1):
            if coverage[midi_note]['missing'] > 0:
                note_name = MidiUtils.midi_to_note_name(midi_note)
                notes_with_gaps.append({
                    'midi': midi_note,
                    'note': note_name,
                    'missing': coverage[midi_note]['missing'],
                    'assigned': coverage[midi_note]['assigned'],
                    'layers': coverage[midi_note]['layers']
                })

        # Sort by number of missing samples (descending)
        notes_with_gaps.sort(key=lambda x: x['missing'], reverse=True)

        # Generate report
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("SAMPLE COVERAGE REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")
        report_lines.append(f"Velocity Layers: {velocity_layers}")
        report_lines.append(f"Instrument Range: {MidiUtils.midi_to_note_name(actual_min_midi)} (MIDI {actual_min_midi}) - {MidiUtils.midi_to_note_name(actual_max_midi)} (MIDI {actual_max_midi})")
        report_lines.append(f"Total Notes in Range: {total_notes}")
        report_lines.append("")
        report_lines.append("-" * 80)
        report_lines.append("SUMMARY")
        report_lines.append("-" * 80)
        report_lines.append(f"Total Possible Samples: {total_possible_samples} ({total_notes} notes × {velocity_layers} layers)")
        report_lines.append(f"Assigned Samples:       {total_assigned}")
        report_lines.append(f"Missing Samples:        {total_missing}")
        report_lines.append(f"Coverage:               {(total_assigned / total_possible_samples * 100):.1f}%")
        report_lines.append("")

        if notes_with_gaps:
            report_lines.append("-" * 80)
            report_lines.append(f"MISSING SAMPLES ({len(notes_with_gaps)} notes with gaps)")
            report_lines.append("-" * 80)
            report_lines.append(f"{'Note':<8} {'MIDI':<6} {'Missing':<10} {'Assigned':<10} {'Layers'}")
            report_lines.append("-" * 80)

            for note_info in notes_with_gaps:
                layers_str = ', '.join(map(str, note_info['layers'])) if note_info['layers'] else "none"
                report_lines.append(
                    f"{note_info['note']:<8} {note_info['midi']:<6} "
                    f"{note_info['missing']:<10} {note_info['assigned']:<10} {layers_str}"
                )
        else:
            report_lines.append("-" * 80)
            report_lines.append("✓ FULL COVERAGE - All notes have all velocity layers assigned!")
            report_lines.append("-" * 80)

        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("NOTES TO SAMPLE (prioritized by gap count)")
        report_lines.append("=" * 80)

        if notes_with_gaps:
            # Group by missing count
            by_missing_count = defaultdict(list)
            for note_info in notes_with_gaps:
                by_missing_count[note_info['missing']].append(note_info['note'])

            for missing_count in sorted(by_missing_count.keys(), reverse=True):
                notes_list = ', '.join(by_missing_count[missing_count])
                report_lines.append(f"\n{missing_count} layer(s) missing: {notes_list}")
        else:
            report_lines.append("\nNo samples needed - full coverage achieved!")

        report_lines.append("")
        report_lines.append("=" * 80)

        # Write report to file
        report_path = self.output_folder / "samples-report.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

        return report_path

    def cancel_export(self):
        """Zruší probíhající export."""
        self._is_cancelled = True
        logger.info("Export cancellation requested")
        self.progress_updated.emit(0, "Rušení exportu...")