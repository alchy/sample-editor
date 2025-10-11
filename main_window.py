"""
main_window.py - Hlavní okno aplikace s menu lištou a session managementem - OPRAVENÁ VERZE
"""

import logging
from pathlib import Path
from typing import List
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout,
                               QWidget, QPushButton, QLabel, QFileDialog, QProgressBar,
                               QSplitter, QMessageBox, QGroupBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence

# Import všech potřebných modulů
from models import SampleMetadata
from export_utils import ExportManager
from export_thread import ExportThread
from session_manager import SessionManager
from session_dialog import SessionDialog
from session_aware_analyzer import SessionAwareBatchAnalyzer

# Import UI komponent
from drag_drop_sample_list import DragDropSampleList
from drag_drop_mapping_matrix import DragDropMappingMatrix
from audio_player import AudioPlayer

logger = logging.getLogger(__name__)


class ControlPanel(QGroupBox):
    """Zjednodušený kontejner pro session info a export."""

    def __init__(self):
        super().__init__("Session & Export")
        self.init_ui()

    def init_ui(self):
        """Inicializace zjednodušeného panelu."""
        layout = QHBoxLayout()

        # Session info
        session_label = QLabel("Session:")
        session_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        layout.addWidget(session_label)

        self.session_name_label = QLabel("No session")
        self.session_name_label.setStyleSheet("color: #3498db; font-weight: bold;")
        layout.addWidget(self.session_name_label)

        layout.addStretch()

        # Export button
        self.btn_export = QPushButton("Export")
        self.btn_export.setEnabled(False)
        self.btn_export.setMaximumWidth(80)
        self.btn_export.setStyleSheet(
            "QPushButton:enabled { background-color: #4CAF50; color: white; font-weight: bold; }")
        layout.addWidget(self.btn_export)

        # Cancel button (skrytý dokud neprobíhá export)
        self.btn_cancel_export = QPushButton("Cancel")
        self.btn_cancel_export.setVisible(False)
        self.btn_cancel_export.setMaximumWidth(80)
        self.btn_cancel_export.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; font-weight: bold; }")
        layout.addWidget(self.btn_cancel_export)

        self.setLayout(layout)
        self.setMaximumHeight(60)

    def set_session_name(self, session_name: str):
        """Nastaví název aktuální session."""
        self.session_name_label.setText(session_name)

    def enable_export(self, enabled: bool):
        """Povolí/zakáže export button."""
        self.btn_export.setEnabled(enabled)

    def set_export_mode(self, exporting: bool):
        """Přepne UI do/z export módu."""
        self.btn_export.setVisible(not exporting)
        self.btn_cancel_export.setVisible(exporting)


class StatusPanel(QGroupBox):
    """Kontejner pro status informace s cache statistikami."""

    def __init__(self):
        super().__init__("Status")
        self.init_ui()

    def init_ui(self):
        """Inicializace status panelu."""
        layout = QVBoxLayout()

        self.status_label = QLabel("Ready. Please select a session to begin.")
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
            self.cache_label.setText(
                f"Cache: {cached_count} samples loaded from cache, {analyzed_count} newly analyzed")
        else:
            self.cache_label.setText("")


class MainWindow(QMainWindow):
    """Hlavní okno aplikace s menu lištou."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sampler Editor - Professional Version")
        self.resize(1600, 900)

        self.samples = []
        self.export_manager = None
        self.export_thread = None
        self.session_manager = SessionManager()
        self.input_folder = None
        self.output_folder = None

        # Audio player
        self.audio_player = AudioPlayer()

        # Show session dialog first
        if not self._show_session_dialog():
            import sys
            sys.exit(0)

        self._create_menu_bar()
        self.init_ui()
        self.connect_signals()
        self._restore_session_state()

    def _create_menu_bar(self):
        """Vytvoří profesionální menu lištu."""
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")

        # New Session
        new_session_action = QAction("&New Session...", self)
        new_session_action.setShortcut(QKeySequence.StandardKey.New)
        new_session_action.setStatusTip("Create a new session")
        new_session_action.triggered.connect(self._new_session)
        file_menu.addAction(new_session_action)

        file_menu.addSeparator()

        # Set Input Folder
        input_folder_action = QAction("Set &Input Folder...", self)
        input_folder_action.setShortcut(QKeySequence("Ctrl+I"))
        input_folder_action.setStatusTip("Select folder containing audio samples")
        input_folder_action.triggered.connect(self._select_input_folder)
        file_menu.addAction(input_folder_action)

        # Set Output Folder
        output_folder_action = QAction("Set &Output Folder...", self)
        output_folder_action.setShortcut(QKeySequence("Ctrl+O"))
        output_folder_action.setStatusTip("Select output folder for exported samples")
        output_folder_action.triggered.connect(self._select_output_folder)
        file_menu.addAction(output_folder_action)

        file_menu.addSeparator()

        # Export
        self.export_action = QAction("&Export Samples", self)
        self.export_action.setShortcut(QKeySequence("Ctrl+E"))
        self.export_action.setStatusTip("Export mapped samples to output folder")
        self.export_action.setEnabled(False)
        self.export_action.triggered.connect(self.export_samples)
        file_menu.addAction(self.export_action)

        file_menu.addSeparator()

        # Exit
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit Menu
        edit_menu = menubar.addMenu("&Edit")

        # Clear Matrix
        clear_matrix_action = QAction("&Clear Matrix", self)
        clear_matrix_action.setShortcut(QKeySequence("Ctrl+K"))
        clear_matrix_action.setStatusTip("Clear all mapped samples from matrix")
        clear_matrix_action.triggered.connect(self._clear_matrix)
        edit_menu.addAction(clear_matrix_action)

        # View Menu
        view_menu = menubar.addMenu("&View")

        # Refresh Samples
        refresh_action = QAction("&Refresh Samples", self)
        refresh_action.setShortcut(QKeySequence.StandardKey.Refresh)
        refresh_action.setStatusTip("Refresh sample list")
        refresh_action.triggered.connect(self._refresh_samples)
        view_menu.addAction(refresh_action)

        # Help Menu
        help_menu = menubar.addMenu("&Help")

        # About
        about_action = QAction("&About", self)
        about_action.setStatusTip("About Sampler Editor")
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

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
            self.status_panel.update_status(
                f"Session '{session_info['name']}' loaded. Cached: {session_info['cached_samples']} samples.")

        # Restore folder paths
        self.input_folder, self.output_folder = self.session_manager.get_folders()

        # Set up export manager if output folder exists
        if self.output_folder:
            self.set_output_folder(self.output_folder, emit_signal=False)

        # Auto-load input folder if exists
        if self.input_folder and self.input_folder.exists():
            QTimer.singleShot(100, lambda: self.load_samples(self.input_folder))

    def init_ui(self):
        """Inicializace hlavního UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Zjednodušený control panel
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

        # Status bar
        self.statusBar().showMessage("Ready")

    def connect_signals(self):
        """Připojí signály."""
        self.control_panel.btn_export.clicked.connect(self.export_samples)
        self.control_panel.btn_cancel_export.clicked.connect(self.cancel_export)

        # Sample list signály
        self.sample_list.sample_selected.connect(self._on_sample_selected)
        self.sample_list.midi_changed.connect(self._on_midi_note_changed)  # NOVÉ PROPOJENÍ!

        # Matrix signály
        self.mapping_matrix.sample_selected_in_matrix.connect(self.sample_list.highlight_sample_in_list)
        self.mapping_matrix.sample_mapped.connect(self._on_sample_mapped)
        self.mapping_matrix.sample_unmapped.connect(self._on_sample_unmapped)
        self.mapping_matrix.sample_moved.connect(self._on_sample_moved)

        # Audio signály
        self.mapping_matrix.sample_play_requested.connect(self.safe_play_sample)
        self.mapping_matrix.midi_note_play_requested.connect(self.audio_player.play_midi_tone)
        self.sample_list.sample_selected.connect(self.audio_player.set_current_sample)

    # Menu action handlers
    def _new_session(self):
        """Vytvoří novou session."""
        if self.session_manager.session_data:
            self._save_session_state()

        self.session_manager.close_session()

        if self._show_session_dialog():
            self.samples = []
            self.sample_list.update_samples([])
            self.mapping_matrix.clear_matrix()
            self._restore_session_state()

    def _select_input_folder(self):
        """Výběr vstupní složky."""
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if folder:
            self.input_folder = Path(folder)
            self.session_manager.save_folders(input_folder=self.input_folder)
            self.load_samples(self.input_folder)
            self.statusBar().showMessage(f"Input folder: {self.input_folder.name}")

    def _select_output_folder(self):
        """Výběr výstupní složky."""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = Path(folder)
            self.set_output_folder(self.output_folder)
            self.statusBar().showMessage(f"Output folder: {self.output_folder.name}")

    def _clear_matrix(self):
        """Vyčistí mapovací matici."""
        reply = QMessageBox.question(self, "Clear Matrix",
                                     "Are you sure you want to clear all mapped samples?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.mapping_matrix.clear_matrix()
            self.sample_list.refresh_display()
            self._save_session_state()
            self.statusBar().showMessage("Matrix cleared")

    def _refresh_samples(self):
        """Obnoví seznam samples."""
        if self.input_folder:
            self.load_samples(self.input_folder)
        else:
            QMessageBox.information(self, "Refresh Samples", "Please select an input folder first.")

    def _show_about(self):
        """Zobrazí About dialog."""
        QMessageBox.about(self, "About Sampler Editor",
                          "Sampler Editor v2.0\n\n"
                          "Professional sample mapping tool with:\n"
                          "• CREPE pitch detection\n"
                          "• RMS velocity analysis\n"
                          "• Hash-based session caching\n"
                          "• Drag & drop interface\n"
                          "• Multi-format export\n\n"
                          "Built with PySide6 and Python")

    # Core functionality methods
    def safe_play_sample(self, sample: SampleMetadata):
        """Bezpečné přehrání sample."""
        try:
            self.audio_player.stop_playback()
            QTimer.singleShot(50, lambda: self.audio_player.play_sample(sample))
        except Exception as e:
            logger.error(f"Error playing sample {sample.filename}: {e}")

    def load_samples(self, input_folder: Path):
        """Načte samples se session cachingem."""
        self.status_panel.show_progress()
        self.status_panel.update_progress(0, "Starting analysis with cache...")

        self.session_manager.save_folders(input_folder=input_folder)

        # Reset samples list pro nové načítání
        self.samples = []
        self.sample_list.update_samples([])

        self.analyzer = SessionAwareBatchAnalyzer(input_folder, self.session_manager)
        self.analyzer.progress_updated.connect(self.status_panel.update_progress)
        self.analyzer.sample_analyzed.connect(self._on_sample_analyzed)  # NOVÝ signál!
        self.analyzer.analysis_completed.connect(self._on_analysis_completed)
        self.analyzer.start()

    def _on_sample_analyzed(self, sample: SampleMetadata, range_info: dict):
        """
        NOVÝ HANDLER: Průběžně přidává analyzované samples do seznamu.

        Args:
            sample: Nově analyzovaný nebo načtený sample
            range_info: Aktuální informace o amplitude rozsahu
        """
        # Přidej sample do seznamu
        self.samples.append(sample)

        # Průběžně aktualizuj UI (každých 10 samples nebo při posledním)
        if len(self.samples) % 10 == 0 or len(self.samples) == 1:
            self.sample_list.update_samples(self.samples)
            logger.debug(f"UI updated with {len(self.samples)} samples")

    def _on_analysis_completed(self, samples: List[SampleMetadata], range_info: dict):
        """Handler pro dokončení analýzy."""
        # Samples už jsou přidány průběžně v _on_sample_analyzed
        # Jen se ujistíme že máme finální seznam (pro případ že něco chybělo)
        if not self.samples:
            self.samples = [s for s in samples if s is not None]

        self.status_panel.hide_progress()

        if not self.samples:
            self.status_panel.update_status("No valid samples found")
            return

        # EXPLICITNÍ CACHE UKLÁDÁNÍ - ujisti se že se data uloží
        logger.info(f"Explicitly caching {len(self.samples)} samples after analysis...")

        # Rozdel samples na cached a newly analyzed
        cached_count = len(self.analyzer.cached_samples) if hasattr(self.analyzer, 'cached_samples') else 0
        newly_analyzed = self.samples[cached_count:] if cached_count > 0 else self.samples

        logger.info(f"Analysis stats: {cached_count} cached, {len(newly_analyzed)} newly analyzed")

        # Ujisti se že newly analyzed samples mají hash a jsou označené jako analyzed
        samples_to_cache = []
        for sample in newly_analyzed:
            if not hasattr(sample, '_hash'):
                # Pokud sample nemá hash, spočítej ho
                try:
                    file_hash = self.session_manager._calculate_file_hash(sample.filepath)
                    sample._hash = file_hash
                    logger.debug(f"Calculated missing hash for {sample.filename}: {file_hash[:8]}...")
                except Exception as e:
                    logger.error(f"Failed to calculate hash for {sample.filename}: {e}")
                    continue

            # Ujisti se že je označený jako analyzed
            sample.analyzed = True
            samples_to_cache.append(sample)

        # Cache všechny nově analyzované samples
        if samples_to_cache:
            self.session_manager.cache_analyzed_samples(samples_to_cache)
            logger.info(f"Successfully cached {len(samples_to_cache)} samples")
        else:
            logger.warning("No samples to cache - all samples missing hash or failed validation")

        # Finální update UI (samples už byly průběžně přidávány)
        self.sample_list.update_samples(self.samples)
        self.mapping_matrix.clear_matrix()

        # Show cache statistics
        self.status_panel.update_cache_info(cached_count, len(newly_analyzed))
        logger.info(f"UI finalized with {len(self.samples)} total samples")

        # Restore mapping
        restored_mapping = self.session_manager.restore_mapping(self.samples)
        if restored_mapping:
            for (midi, velocity), sample in restored_mapping.items():
                self.mapping_matrix.add_sample(sample, midi, velocity)

            self.status_panel.update_status(
                f"Session restored: {len(self.samples)} samples, {len(restored_mapping)} mappings")
        else:
            self.status_panel.update_status(f"Analysis completed: {len(self.samples)} samples loaded")

        # EXPLICITNÍ ULOŽENÍ SESSION
        self._save_session_state()

        # Debug: Zkontroluj že se data skutečně uložila
        session_info = self.session_manager.get_session_info()
        if session_info:
            logger.info(f"Session after analysis: {session_info['cached_samples']} cached samples, "
                       f"{session_info['mapping_entries']} mapping entries")

        self.update_export_button_state()

    def set_output_folder(self, output_folder: Path, emit_signal: bool = True):
        """Nastaví výstupní složku."""
        self.export_manager = ExportManager(output_folder)
        if self.export_manager.validate_export_folder():
            if emit_signal:
                self.status_panel.update_status(f"Output folder set: {output_folder.name}")

            self.session_manager.save_folders(output_folder=output_folder)
            self.update_export_button_state()
        else:
            QMessageBox.warning(self, "Error", "Output folder is not writable")
            self.export_manager = None

    def update_export_button_state(self):
        """Aktualizuje stav export buttonu."""
        has_output = self.export_manager is not None
        has_mapped = len(self.mapping_matrix.get_mapped_samples()) > 0
        enabled = has_output and has_mapped

        self.control_panel.enable_export(enabled)
        self.export_action.setEnabled(enabled)

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
            QMessageBox.critical(self, "Export Error", f"Cannot start export:\n{e}")

    def cancel_export(self):
        """Zruší export."""
        if self.export_thread and self.export_thread.isRunning():
            self.export_thread.cancel_export()
            self.export_thread.wait(3000)
            self.control_panel.set_export_mode(False)
            self.status_panel.hide_progress()
            self.status_panel.update_status("Export cancelled")

    def _on_export_completed(self, export_info: dict):
        """Handler pro dokončení exportu."""
        self.control_panel.set_export_mode(False)
        self.status_panel.hide_progress()

        message = (f"Export completed!\n\n"
                   f"Exported: {export_info['exported_count']} samples\n"
                   f"Total files: {export_info['total_files']}\n"
                   f"Folder: {self.export_manager.output_folder}")

        if export_info['failed_count'] > 0:
            message += f"\n\nErrors: {export_info['failed_count']} samples"

        QMessageBox.information(self, "Export Completed", message)
        self.status_panel.update_status(f"Export completed: {export_info['exported_count']} samples")

    def _on_export_failed(self, error_message: str):
        """Handler pro selhání exportu."""
        self.control_panel.set_export_mode(False)
        self.status_panel.hide_progress()
        self.status_panel.update_status("Export failed")
        QMessageBox.critical(self, "Export Error", f"Export failed:\n\n{error_message}")

    def _on_sample_selected(self, sample: SampleMetadata):
        """Handler pro výběr sample."""
        self.mapping_matrix.highlight_sample_in_matrix(sample)

    def _on_sample_mapped(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """Handler pro mapování sample."""
        self.sample_list.refresh_display()
        self.update_export_button_state()
        self._save_session_state()

    def _on_sample_unmapped(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """Handler pro unmapování sample."""
        self.sample_list.refresh_display()
        self.update_export_button_state()
        self._save_session_state()

    def _on_sample_moved(self, sample: SampleMetadata, old_midi: int, old_velocity: int, new_midi: int,
                         new_velocity: int):
        """Handler pro přesun sample."""
        self.sample_list.refresh_display()
        self._save_session_state()

    def _on_midi_note_changed(self, sample: SampleMetadata, old_midi: int, new_midi: int):
        """
        NOVÁ METODA: Handler pro změnu MIDI noty v inline editoru.
        Propojuje transpozici s session managementem.
        """
        logger.info(f"MIDI note changed for {sample.filename}: {old_midi} -> {new_midi}")

        # Aktualizuj sample v session cache
        self.session_manager.update_sample_pitch(sample, old_midi, new_midi)

        # Refresh UI
        self.sample_list.refresh_display()

        # Pokud je sample namapován, může být potřeba aktualizovat mapping
        if sample.mapped:
            # Najdi kde je sample namapován a potenciálně ho přesuň
            current_mapping = self.mapping_matrix.get_mapped_samples()
            for (midi, velocity), mapped_sample in current_mapping.items():
                if mapped_sample == sample and midi == old_midi:
                    # Sample je namapován na starou MIDI notu - možná ho chceme přesunout?
                    # Pro jednoduchost necháme uživatele ručně přesunout
                    logger.info(f"Sample {sample.filename} is mapped on old MIDI {old_midi}, "
                              f"consider remapping to new MIDI {new_midi}")
                    break

        # Uložit změny do session
        self._save_session_state()

    def _save_session_state(self):
        """Uloží aktuální stav do session."""
        if self.session_manager.session_data:
            current_mapping = self.mapping_matrix.get_mapped_samples()
            self.session_manager.save_mapping(current_mapping)

    def closeEvent(self, event):
        """Handler pro zavření aplikace."""
        # EXPLICITNÍ ULOŽENÍ VŠECH DAT před zavřením
        logger.info("Closing application - saving all session data...")

        # 1. Ulož mapping
        self._save_session_state()

        # 2. NOVÉ: Ulož VŠECHNY samples do cache (i ty které už byly cached)
        #    Tím zajistíme že se uloží i transpozice a další změny
        if self.samples and self.session_manager.session_data:
            logger.info(f"Saving {len(self.samples)} samples to cache before closing...")
            try:
                self.session_manager.cache_analyzed_samples(self.samples)
                logger.info("✓ All samples cached successfully")
            except Exception as e:
                logger.error(f"Failed to cache samples on close: {e}")

        # 3. Finální explicitní close session (vyvolá _save_session())
        self.session_manager.close_session()
        logger.info("✓ Session closed and saved")

        if self.export_thread and self.export_thread.isRunning():
            self.cancel_export()

        if self.audio_player:
            self.audio_player.cleanup()

        if hasattr(self, 'analyzer') and self.analyzer.isRunning():
            self.analyzer.stop_analysis()
            self.analyzer.wait(3000)

        event.accept()