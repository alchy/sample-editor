"""
main.py - Sampler Editor s kompletním session managementem a hash cachingem
"""

import sys
import logging
from pathlib import Path
from typing import List, Set
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                               QWidget, QPushButton, QLabel, QFileDialog, QProgressBar,
                               QSplitter, QMessageBox, QGroupBox, QFrame)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

# Import všech potřebných modulů
from models import SampleMetadata
from audio_analyzer import BatchAnalyzer
from midi_utils import MidiUtils
from export_utils import ExportManager, ExportValidator
from export_thread import ExportThread
from session_manager import SessionManager
from session_dialog import SessionDialog

# Import REFAKTORIZOVANÝCH komponent s drag tlačítky
from drag_drop_sample_list import DragDropSampleList
from drag_drop_mapping_matrix import DragDropMappingMatrix
from audio_player import AudioPlayer
from amplitude_analyzer import AmplitudeRangeManager

# Nastavení loggingu
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ControlPanel(QGroupBox):
    """Kontejner pro ovládací prvky s session info."""

    input_folder_selected = Signal(object)  # Path
    output_folder_selected = Signal(object)  # Path
    export_requested = Signal()
    new_session_requested = Signal()

    def __init__(self):
        super().__init__("Ovládání")
        self.input_folder = None
        self.output_folder = None
        self.init_ui()

    def init_ui(self):
        """Inicializace ovládacího panelu."""
        layout = QVBoxLayout()

        # Session info řádek
        session_layout = QHBoxLayout()

        session_label = QLabel("Session:")
        session_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        session_layout.addWidget(session_label)

        self.session_name_label = QLabel("Žádná session")
        self.session_name_label.setStyleSheet("color: #3498db; font-weight: bold;")
        session_layout.addWidget(self.session_name_label)

        session_layout.addStretch()

        # New Session button
        self.btn_new_session = QPushButton("Nová Session")
        self.btn_new_session.clicked.connect(self.new_session_requested.emit)
        self.btn_new_session.setMaximumWidth(100)
        self.btn_new_session.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        session_layout.addWidget(self.btn_new_session)

        layout.addLayout(session_layout)

        # Hlavní ovládací řádek
        main_layout = QHBoxLayout()
        main_layout.setSpacing(15)

        # Vstupní složka
        self.btn_input_folder = QPushButton("Vstupní složka...")
        self.btn_input_folder.clicked.connect(self.select_input_folder)
        self.btn_input_folder.setMaximumWidth(120)
        main_layout.addWidget(self.btn_input_folder)

        self.input_folder_label = QLabel("Žádná složka")
        self.input_folder_label.setStyleSheet("color: gray; font-style: italic; font-size: 12px;")
        self.input_folder_label.setMaximumWidth(150)
        main_layout.addWidget(self.input_folder_label)

        # Separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.VLine)
        separator1.setFrameShadow(QFrame.Shadow.Sunken)
        separator1.setMaximumHeight(30)
        main_layout.addWidget(separator1)

        # Výstupní složka
        self.btn_output_folder = QPushButton("Výstupní složka...")
        self.btn_output_folder.clicked.connect(self.select_output_folder)
        self.btn_output_folder.setMaximumWidth(120)
        main_layout.addWidget(self.btn_output_folder)

        self.output_folder_label = QLabel("Žádná složka")
        self.output_folder_label.setStyleSheet("color: gray; font-style: italic; font-size: 12px;")
        self.output_folder_label.setMaximumWidth(150)
        main_layout.addWidget(self.output_folder_label)

        main_layout.addStretch()

        # Export button
        self.btn_export = QPushButton("Export")
        self.btn_export.clicked.connect(self.export_samples)
        self.btn_export.setEnabled(False)
        self.btn_export.setMaximumWidth(80)
        self.btn_export.setStyleSheet(
            "QPushButton:enabled { background-color: #4CAF50; color: white; font-weight: bold; }")
        main_layout.addWidget(self.btn_export)

        # Cancel button (skrytý dokud neprobíhá export)
        self.btn_cancel_export = QPushButton("Zrušit")
        self.btn_cancel_export.clicked.connect(self.cancel_export)
        self.btn_cancel_export.setVisible(False)
        self.btn_cancel_export.setMaximumWidth(80)
        self.btn_cancel_export.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; font-weight: bold; }")
        main_layout.addWidget(self.btn_cancel_export)

        layout.addLayout(main_layout)
        self.setLayout(layout)
        self.setMaximumHeight(80)

    def set_session_name(self, session_name: str):
        """Nastaví název aktuální session."""
        self.session_name_label.setText(session_name)

    def set_folders_from_session(self, input_folder: Path = None, output_folder: Path = None):
        """Nastaví složky ze session bez emitování signálů."""
        if input_folder and input_folder.exists():
            self.input_folder = input_folder
            self.input_folder_label.setText(f"{input_folder.name}")
            self.input_folder_label.setStyleSheet("color: black; font-weight: bold; font-size: 12px;")

        if output_folder and output_folder.exists():
            self.output_folder = output_folder
            self.output_folder_label.setText(f"{output_folder.name}")
            self.output_folder_label.setStyleSheet("color: black; font-weight: bold; font-size: 12px;")

    def select_input_folder(self):
        """Výběr vstupní složky."""
        folder = QFileDialog.getExistingDirectory(self, "Vyberte složku se samples")
        if folder:
            self.input_folder = Path(folder)
            self.input_folder_label.setText(f"{self.input_folder.name}")
            self.input_folder_label.setStyleSheet("color: black; font-weight: bold; font-size: 12px;")
            self.input_folder_selected.emit(self.input_folder)

    def select_output_folder(self):
        """Výběr výstupní složky."""
        folder = QFileDialog.getExistingDirectory(self, "Vyberte výstupní složku")
        if folder:
            self.output_folder = Path(folder)
            self.output_folder_label.setText(f"{self.output_folder.name}")
            self.output_folder_label.setStyleSheet("color: black; font-weight: bold; font-size: 12px;")
            self.output_folder_selected.emit(self.output_folder)

    def export_samples(self):
        """Signál pro export."""
        self.export_requested.emit()

    def cancel_export(self):
        """Signál pro zrušení exportu."""
        if hasattr(self, 'parent') and hasattr(self.parent(), 'cancel_export'):
            self.parent().cancel_export()

    def enable_export(self, enabled: bool):
        """Povolí/zakáže export button."""
        self.btn_export.setEnabled(enabled)

    def set_export_mode(self, exporting: bool):
        """Přepne UI do/z export módu."""
        self.btn_export.setVisible(not exporting)
        self.btn_cancel_export.setVisible(exporting)
        self.btn_input_folder.setEnabled(not exporting)
        self.btn_output_folder.setEnabled(not exporting)
        self.btn_new_session.setEnabled(not exporting)


class StatusPanel(QGroupBox):
    """Kontejner pro status informace s cache statistikami."""

    def __init__(self):
        super().__init__("Status")
        self.init_ui()

    def init_ui(self):
        """Inicializace status panelu."""
        layout = QVBoxLayout()

        self.status_label = QLabel("Připraven. Vyberte session pro začátek.")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Cache info label
        self.cache_label = QLabel("")
        self.cache_label.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        layout.addWidget(self.cache_label)

        self.setLayout(layout)
        self.setMaximumHeight(120)

    def update_status(self, message: str):
        """Aktualizuje statusovou zprávu."""
        self.status_label.setText(message)

    def update_progress(self, percentage: int, message: str):
        """Aktualizuje progress bar."""
        self.progress_bar.setValue(percentage)
        self.update_status(message)
        if percentage >= 100:
            self.progress_bar.setVisible(False)
        else:
            self.progress_bar.setVisible(True)

    def show_progress(self):
        """Zobrazí progress bar."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

    def hide_progress(self):
        """Skryje progress bar."""
        self.progress_bar.setVisible(False)

    def update_cache_info(self, cached_count: int, analyzed_count: int):
        """Aktualizuje informace o cache."""
        if cached_count > 0:
            self.cache_label.setText(f"Cache: {cached_count} samples načteno z cache, {analyzed_count} nově analyzováno")
        else:
            self.cache_label.setText("")


# Vylepšený BatchAnalyzer s session cachingem
class SessionAwareBatchAnalyzer(BatchAnalyzer):
    """BatchAnalyzer s podporou session cache."""

    def __init__(self, input_folder: Path, session_manager: SessionManager):
        super().__init__(input_folder)
        self.session_manager = session_manager
        self.cached_samples = []
        self.samples_to_analyze = []

    def run(self):
        """Spustí analýzu s využitím cache."""
        try:
            # Najdi audio soubory
            audio_files = self._find_unique_audio_files()
            if not audio_files:
                self.progress_updated.emit(0, "Žádné audio soubory nenalezeny")
                self.analysis_completed.emit([], {})
                return

            logger.info(f"Found {len(audio_files)} unique audio files")

            # Vytvoř SampleMetadata objekty
            samples = [SampleMetadata(filepath) for filepath in audio_files]

            # Zkontroluj cache
            self.progress_updated.emit(5, "Kontrola cache...")
            self.cached_samples, self.samples_to_analyze = self.session_manager.analyze_folder_with_cache(
                self.input_folder, samples
            )

            logger.info(f"Cache analysis: {len(self.cached_samples)} cached, {len(self.samples_to_analyze)} to analyze")

            if not self.samples_to_analyze:
                # Vše je v cache
                self.progress_updated.emit(100, f"Všechny samples načteny z cache ({len(self.cached_samples)} samples)")

                # Setup amplitude range manager
                range_manager = AmplitudeRangeManager()
                for sample in self.cached_samples:
                    if sample.velocity_amplitude:
                        range_manager.add_sample_amplitude(sample.velocity_amplitude)

                range_info = range_manager.get_range_info()
                self.analysis_completed.emit(self.cached_samples, range_info)
                return

            # Analyzuj jen nové samples pomocí vlastní logiky (ne parent's run())
            self.progress_updated.emit(10, f"Analyzuji {len(self.samples_to_analyze)} nových samples...")
            self._analyze_samples_directly(self.samples_to_analyze)

        except Exception as e:
            logger.error(f"SessionAwareBatchAnalyzer failed: {e}", exc_info=True)
            self.analysis_completed.emit([], {})

    def _analyze_samples_directly(self, samples_to_analyze):
        """Analyzuje samples přímo bez volání parent run()."""
        try:
            # Reset amplitude range manager
            self.amplitude_range_manager.reset()

            total_samples = len(samples_to_analyze)
            analyzed_samples = []

            for i, sample in enumerate(samples_to_analyze):
                try:
                    # Update progress
                    percentage = 15 + int(((i + 1) / total_samples) * 80)  # 15-95%
                    self.progress_updated.emit(percentage, f"Analyzuji: {sample.filename}")

                    # Analyze single sample using parent's method
                    analyzed_sample = self._analyze_single_sample(sample.filepath)

                    if analyzed_sample:
                        analyzed_samples.append(analyzed_sample)

                        # Add to amplitude range manager
                        if analyzed_sample.velocity_amplitude is not None and analyzed_sample.velocity_amplitude > 0:
                            self.amplitude_range_manager.add_sample_amplitude(analyzed_sample.velocity_amplitude)

                except Exception as e:
                    logger.error(f"Failed to analyze {sample.filepath}: {e}")
                    continue

            # Cache the newly analyzed samples
            if analyzed_samples:
                self.session_manager.cache_analyzed_samples(analyzed_samples)

            # Merge cached and newly analyzed samples
            all_samples = self.cached_samples + analyzed_samples

            # Create final range info with all samples
            final_range_manager = AmplitudeRangeManager()
            for sample in all_samples:
                if sample.velocity_amplitude and sample.velocity_amplitude > 0:
                    final_range_manager.add_sample_amplitude(sample.velocity_amplitude)

            final_range_info = final_range_manager.get_range_info()

            # Final progress update
            self.progress_updated.emit(100, f"Analýza dokončena: {len(all_samples)} samples")

            # Emit completed signal
            self.analysis_completed.emit(all_samples, final_range_info)

        except Exception as e:
            logger.error(f"Direct analysis failed: {e}", exc_info=True)
            self.analysis_completed.emit([], {})

    def _find_unique_audio_files(self) -> List[Path]:
        """Najde unikátní audio soubory bez duplicit."""
        audio_files_set: Set[Path] = set()
        for ext in self.supported_extensions:
            found_files = list(self.input_folder.glob(ext))
            audio_files_set.update(found_files)
        return sorted(list(audio_files_set))


class MainWindow(QMainWindow):
    """Hlavní okno aplikace se session managementem."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sampler Editor - Se Session Managementem")
        self.resize(1600, 900)

        self.samples = []
        self.export_manager = None
        self.export_thread = None
        self.session_manager = SessionManager()

        # Audio player
        self.audio_player = AudioPlayer()

        # Show session dialog first
        if not self._show_session_dialog():
            # User cancelled session dialog
            sys.exit(0)

        self.init_ui()
        self.connect_signals()
        self._restore_session_state()

    def _show_session_dialog(self) -> bool:
        """Zobrazí session dialog a inicializuje session."""
        session_dialog = SessionDialog(self.session_manager, self)

        if session_dialog.exec() == SessionDialog.DialogCode.Accepted:
            session_name = session_dialog.get_selected_session()
            if session_name:
                logger.info(f"Session initialized: {session_name}")
                return True

        return False

    def _restore_session_state(self):
        """Obnoví stav ze session."""
        # Update session name in UI
        session_info = self.session_manager.get_session_info()
        if session_info:
            self.control_panel.set_session_name(session_info['name'])
            self.status_panel.update_status(f"Session '{session_info['name']}' načtena. Cached: {session_info['cached_samples']} samples.")

        # Restore folder paths
        input_folder, output_folder = self.session_manager.get_folders()
        self.control_panel.set_folders_from_session(input_folder, output_folder)

        # Set up export manager if output folder exists
        if output_folder:
            self.set_output_folder(output_folder, emit_signal=False)

        # Auto-load input folder if exists
        if input_folder and input_folder.exists():
            QTimer.singleShot(100, lambda: self.load_samples(input_folder))

    def init_ui(self):
        """Inicializace hlavního UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Horní control panel
        self.control_panel = ControlPanel()
        main_layout.addWidget(self.control_panel)

        # Status panel
        self.status_panel = StatusPanel()
        main_layout.addWidget(self.status_panel)

        # Splitter pro levý a pravý sloupec
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Levý sloupec: Sample list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(2, 2, 2, 2)

        self.sample_list = DragDropSampleList()
        self.sample_list.setMinimumWidth(300)
        self.sample_list.setMaximumWidth(600)
        left_layout.addWidget(self.sample_list)

        splitter.addWidget(left_widget)

        # Pravý sloupec: Mapping matrix + Audio player
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(2, 2, 2, 2)

        self.mapping_matrix = DragDropMappingMatrix()
        self.mapping_matrix.setMinimumWidth(800)
        right_layout.addWidget(self.mapping_matrix)

        # Audio player
        right_layout.addWidget(self.audio_player)

        splitter.addWidget(right_widget)

        # 30/70 rozložení
        splitter.setSizes([480, 1120])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)

        main_layout.addWidget(splitter)

    def connect_signals(self):
        """Připojí signály."""
        self.control_panel.input_folder_selected.connect(self.load_samples)
        self.control_panel.output_folder_selected.connect(self.set_output_folder)
        self.control_panel.export_requested.connect(self.export_samples)
        self.control_panel.new_session_requested.connect(self._new_session)

        # Sample list signály
        self.sample_list.sample_selected.connect(self._on_sample_selected)

        # Matrix signály
        self.mapping_matrix.sample_selected_in_matrix.connect(self.sample_list.highlight_sample_in_list)
        self.mapping_matrix.sample_mapped.connect(self._on_sample_mapped)
        self.mapping_matrix.sample_unmapped.connect(self._on_sample_unmapped)
        self.mapping_matrix.sample_moved.connect(self._on_sample_moved)

        # Audio signály
        self.mapping_matrix.sample_play_requested.connect(self.safe_play_sample)
        self.mapping_matrix.midi_note_play_requested.connect(self.audio_player.play_midi_tone)
        self.sample_list.sample_selected.connect(self.audio_player.set_current_sample)

    def _new_session(self):
        """Vytvoří novou session."""
        # Save current session
        if self.session_manager.session_data:
            self._save_session_state()

        # Close current session
        self.session_manager.close_session()

        # Show session dialog
        if self._show_session_dialog():
            # Reset UI
            self.samples = []
            self.sample_list.update_samples([])
            self.mapping_matrix.clear_matrix()
            self._restore_session_state()
        else:
            # User cancelled, reload previous session if available
            logger.warning("User cancelled new session creation")

    def safe_play_sample(self, sample: SampleMetadata):
        """Bezpečné přehrání sample."""
        try:
            self.audio_player.stop_playback()
            QTimer.singleShot(50, lambda: self.audio_player.play_sample(sample))
        except Exception as e:
            logger.error(f"Error playing sample {sample.filename}: {e}")

    def safe_stop_audio(self):
        """Bezpečné zastavení audio."""
        try:
            self.audio_player.stop_playback()
        except Exception as e:
            logger.error(f"Error stopping audio: {e}")

    def load_samples(self, input_folder: Path):
        """Načte samples se session cachingem."""
        self.status_panel.show_progress()
        self.status_panel.update_progress(0, "Zahajuji analýzu s cache...")

        # Save folder to session
        self.session_manager.save_folders(input_folder=input_folder)

        # Use session-aware analyzer
        self.analyzer = SessionAwareBatchAnalyzer(input_folder, self.session_manager)
        self.analyzer.progress_updated.connect(self.status_panel.update_progress)
        self.analyzer.analysis_completed.connect(self._on_analysis_completed)
        self.analyzer.start()

    def _on_analysis_completed(self, samples: List[SampleMetadata], range_info: dict):
        """Handler pro dokončení analýzy."""
        self.samples = [s for s in samples if s is not None]
        self.status_panel.hide_progress()

        if not self.samples:
            self.status_panel.update_status("Žádné validní samples nalezeny")
            return

        # OPRAVA: Uložit analyzované samples do cache
        self.session_manager.cache_analyzed_samples(self.samples)
        logger.info(f"Cached {len(self.samples)} samples to session")

        # Update UI with samples
        self.sample_list.update_samples(self.samples)
        self.mapping_matrix.clear_matrix()

        # Show cache statistics
        cached_count = len(self.analyzer.cached_samples) if hasattr(self.analyzer, 'cached_samples') else 0
        analyzed_count = len(self.analyzer.samples_to_analyze) if hasattr(self.analyzer, 'samples_to_analyze') else len(self.samples)
        self.status_panel.update_cache_info(cached_count, analyzed_count)

        # Restore mapping from session
        restored_mapping = self.session_manager.restore_mapping(self.samples)
        if restored_mapping:
            # Apply restored mapping to matrix
            for (midi, velocity), sample in restored_mapping.items():
                self.mapping_matrix.add_sample(sample, midi, velocity)

            logger.info(f"Restored {len(restored_mapping)} mapping entries from session")
            self.status_panel.update_status(f"Session obnovena: {len(self.samples)} samples, {len(restored_mapping)} mapping entries")
        else:
            self.status_panel.update_status(f"Analýza dokončena: {len(self.samples)} samples načteno")

        self.update_export_button_state()

    def set_output_folder(self, output_folder: Path, emit_signal: bool = True):
        """Nastaví výstupní složku."""
        self.export_manager = ExportManager(output_folder)
        if self.export_manager.validate_export_folder():
            if emit_signal:
                self.status_panel.update_status(f"Výstupní složka nastavena: {output_folder.name}")

            # Save to session
            self.session_manager.save_folders(output_folder=output_folder)
            self.update_export_button_state()
        else:
            QMessageBox.warning(self, "Chyba", "Výstupní složka není dostupná pro zápis")
            self.export_manager = None

    def update_export_button_state(self):
        """Aktualizuje stav export buttonu."""
        has_output = self.export_manager is not None
        has_mapped = len(self.mapping_matrix.get_mapped_samples()) > 0
        self.control_panel.enable_export(has_output and has_mapped)

    def export_samples(self):
        """Asynchronní export."""
        if not self.export_manager or not self.mapping_matrix.mapping:
            return

        try:
            self.export_thread = ExportThread(
                mapping=self.mapping_matrix.mapping,
                output_folder=self.export_manager.output_folder
            )

            self.export_thread.progress_updated.connect(self.status_panel.update_progress)
            self.export_thread.export_completed.connect(self._on_export_completed)
            self.export_thread.export_failed.connect(self._on_export_failed)

            self.control_panel.set_export_mode(True)
            self.status_panel.show_progress()
            self.export_thread.start()

        except Exception as e:
            QMessageBox.critical(self, "Chyba exportu", f"Nelze spustit export:\n{e}")

    def cancel_export(self):
        """Zruší export."""
        if self.export_thread and self.export_thread.isRunning():
            self.export_thread.cancel_export()
            self.export_thread.wait(3000)
            self.control_panel.set_export_mode(False)
            self.status_panel.hide_progress()
            self.status_panel.update_status("Export zrušen")

    def _on_export_completed(self, export_info: dict):
        """Handler pro dokončení exportu."""
        self.control_panel.set_export_mode(False)
        self.status_panel.hide_progress()

        message = (f"Export dokončen!\n\n"
                   f"✓ Exportováno: {export_info['exported_count']} samples\n"
                   f"✓ Celkem souborů: {export_info['total_files']}\n"
                   f"📁 Složka: {self.export_manager.output_folder}")

        if export_info['failed_count'] > 0:
            message += f"\n\n⚠️ Chyby: {export_info['failed_count']} samples"

        QMessageBox.information(self, "Export dokončen", message)
        self.status_panel.update_status(f"Export dokončen: {export_info['exported_count']} samples")

    def _on_export_failed(self, error_message: str):
        """Handler pro selhání exportu."""
        self.control_panel.set_export_mode(False)
        self.status_panel.hide_progress()
        self.status_panel.update_status("Export selhal")
        QMessageBox.critical(self, "Chyba exportu", f"Export selhal:\n\n{error_message}")

    def _on_sample_selected(self, sample: SampleMetadata):
        """Handler pro výběr sample."""
        self.mapping_matrix.highlight_sample_in_matrix(sample)

    def _on_sample_mapped(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """Handler pro mapování sample."""
        self.sample_list.refresh_display()
        self.update_export_button_state()
        # Save mapping to session
        self._save_session_state()

    def _on_sample_unmapped(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """Handler pro unmapování sample."""
        self.sample_list.refresh_display()
        self.update_export_button_state()
        # Save mapping to session
        self._save_session_state()

    def _on_sample_moved(self, sample: SampleMetadata, old_midi: int, old_velocity: int, new_midi: int, new_velocity: int):
        """Handler pro přesun sample."""
        self.sample_list.refresh_display()
        # Save mapping to session
        self._save_session_state()

    def _save_session_state(self):
        """Uloží aktuální stav do session."""
        if self.session_manager.session_data:
            # Save current mapping
            current_mapping = self.mapping_matrix.get_mapped_samples()
            self.session_manager.save_mapping(current_mapping)

    def closeEvent(self, event):
        """Handler pro zavření aplikace."""
        # Save session state
        self._save_session_state()

        # Stop export if running
        if self.export_thread and self.export_thread.isRunning():
            self.cancel_export()

        # Cleanup audio
        if self.audio_player:
            self.audio_player.cleanup()

        # Stop analyzer if running
        if hasattr(self, 'analyzer') and self.analyzer.isRunning():
            self.analyzer.stop_analysis()
            self.analyzer.wait(3000)

        logger.info("Application closing")
        event.accept()


def main():
    """Hlavní funkce aplikace."""
    app = QApplication(sys.argv)

    try:
        window = MainWindow()
        window.show()

        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        QMessageBox.critical(None, "Kritická chyba", f"Aplikace selhala:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()