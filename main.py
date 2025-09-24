"""
main.py - Finální konsolidovaná verze Sampler Editoru s asynchronním exportem
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
from export_thread import ExportThread  # NOVÝ IMPORT

# Import REFAKTORIZOVANÝCH komponent s drag tlačítky
from drag_drop_sample_list import DragDropSampleList
from drag_drop_mapping_matrix import DragDropMappingMatrix
from audio_player import AudioPlayer
from amplitude_analyzer import AmplitudeRangeManager

# Nastavení loggingu
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ControlPanel(QGroupBox):
    """Kontejner pro ovládací prvky (horní panel)."""

    input_folder_selected = Signal(object)  # Path
    output_folder_selected = Signal(object)  # Path
    export_requested = Signal()

    def __init__(self):
        super().__init__("Ovládání")
        self.input_folder = None
        self.output_folder = None
        self.init_ui()

    def init_ui(self):
        """Inicializace ovládacího panelu."""
        layout = QHBoxLayout()
        layout.setSpacing(15)

        # Vstupní složka
        self.btn_input_folder = QPushButton("Vstupní složka...")
        self.btn_input_folder.clicked.connect(self.select_input_folder)
        self.btn_input_folder.setMaximumWidth(120)
        layout.addWidget(self.btn_input_folder)

        self.input_folder_label = QLabel("Žádná složka")
        self.input_folder_label.setStyleSheet("color: gray; font-style: italic; font-size: 12px;")
        self.input_folder_label.setMaximumWidth(150)
        layout.addWidget(self.input_folder_label)

        # Separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.VLine)
        separator1.setFrameShadow(QFrame.Shadow.Sunken)
        separator1.setMaximumHeight(30)
        layout.addWidget(separator1)

        # Výstupní složka
        self.btn_output_folder = QPushButton("Výstupní složka...")
        self.btn_output_folder.clicked.connect(self.select_output_folder)
        self.btn_output_folder.setMaximumWidth(120)
        layout.addWidget(self.btn_output_folder)

        self.output_folder_label = QLabel("Žádná složka")
        self.output_folder_label.setStyleSheet("color: gray; font-style: italic; font-size: 12px;")
        self.output_folder_label.setMaximumWidth(150)
        layout.addWidget(self.output_folder_label)

        layout.addStretch()

        # Export button
        self.btn_export = QPushButton("Export")
        self.btn_export.clicked.connect(self.export_samples)
        self.btn_export.setEnabled(False)
        self.btn_export.setMaximumWidth(80)
        self.btn_export.setStyleSheet(
            "QPushButton:enabled { background-color: #4CAF50; color: white; font-weight: bold; }")
        layout.addWidget(self.btn_export)

        # Cancel button (skrytý dokud neprobíhá export)
        self.btn_cancel_export = QPushButton("Zrušit")
        self.btn_cancel_export.clicked.connect(self.cancel_export)
        self.btn_cancel_export.setVisible(False)
        self.btn_cancel_export.setMaximumWidth(80)
        self.btn_cancel_export.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; font-weight: bold; }")
        layout.addWidget(self.btn_cancel_export)

        self.setLayout(layout)
        self.setMaximumHeight(60)

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


class StatusPanel(QGroupBox):
    """Kontejner pro status informace."""

    def __init__(self):
        super().__init__("Status")
        self.init_ui()

    def init_ui(self):
        """Inicializace status panelu."""
        layout = QVBoxLayout()

        self.status_label = QLabel("Připraven. Vyberte vstupní složku se samples.")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)
        self.setMaximumHeight(100)

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


# Vylepšený BatchAnalyzer bez duplicitní detekce
class FixedBatchAnalyzer(BatchAnalyzer):
    """BatchAnalyzer s opravou duplicitní detekce souborů."""

    def run(self):
        """Spustí batch analýzu s opravou duplicit."""
        try:
            # Najdi audio soubory bez duplicit
            audio_files = self._find_unique_audio_files()

            if not audio_files:
                self.progress_updated.emit(0, "Žádné audio soubory nenalezeny")
                self.analysis_completed.emit([], {})
                return

            logger.info(f"Nalezeno {len(audio_files)} unikátních audio souborů")

            # Pokračuj s původní logikou
            super().run()

        except Exception as e:
            logger.error(f"Chyba při batch analýze: {e}", exc_info=True)
            self.analysis_completed.emit([], {})

    def _find_unique_audio_files(self) -> List[Path]:
        """Najde unikátní audio soubory bez duplicit."""
        audio_files_set: Set[Path] = set()

        for ext in self.supported_extensions:
            found_files = list(self.input_folder.glob(ext))
            audio_files_set.update(found_files)
            logger.debug(f"Extension {ext}: found {len(found_files)} files")

        return sorted(list(audio_files_set))


class MainWindow(QMainWindow):
    """Hlavní okno aplikace s asynchronním exportem."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sampler Editor - S asynchronním exportem")
        self.resize(1600, 900)

        self.samples = []
        self.export_manager = None
        self.export_thread = None  # NOVÝ ATRIBUT

        # Audio player
        self.audio_player = AudioPlayer()

        self.init_ui()
        self.connect_signals()

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

        # Levý sloupec: Sample list s drag tlačítky (30%)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(2, 2, 2, 2)

        self.sample_list = DragDropSampleList()
        self.sample_list.setMinimumWidth(300)
        self.sample_list.setMaximumWidth(600)
        left_layout.addWidget(self.sample_list)

        splitter.addWidget(left_widget)

        # Pravý sloupec: Mapping matrix + Audio player (70%)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(2, 2, 2, 2)

        self.mapping_matrix = DragDropMappingMatrix()
        self.mapping_matrix.setMinimumWidth(800)
        right_layout.addWidget(self.mapping_matrix)

        # Audio player dole vpravo
        right_layout.addWidget(self.audio_player)

        splitter.addWidget(right_widget)

        # 30/70 rozložení
        total_width = 1600
        sample_list_width = int(total_width * 0.3)
        matrix_width = int(total_width * 0.7)

        splitter.setSizes([sample_list_width, matrix_width])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)

        main_layout.addWidget(splitter)

    def connect_signals(self):
        """Připojí signály."""
        self.control_panel.input_folder_selected.connect(self.load_samples)
        self.control_panel.output_folder_selected.connect(self.set_output_folder)
        self.control_panel.export_requested.connect(self.export_samples)

        # Sample list signály
        self.sample_list.sample_selected.connect(self._on_sample_selected)

        # Matrix signály
        self.mapping_matrix.sample_selected_in_matrix.connect(self.sample_list.highlight_sample_in_list)
        self.mapping_matrix.sample_mapped.connect(self._on_sample_mapped)
        self.mapping_matrix.sample_unmapped.connect(self._on_sample_unmapped)
        self.mapping_matrix.sample_moved.connect(self._on_sample_moved)

        # Audio signály z matice
        self.mapping_matrix.sample_play_requested.connect(self.safe_play_sample)
        self.mapping_matrix.midi_note_play_requested.connect(self.audio_player.play_midi_tone)

        # Audio player nastav jako aktuální sample
        self.sample_list.sample_selected.connect(self.audio_player.set_current_sample)

    def safe_play_sample(self, sample: SampleMetadata):
        """Bezpečné přehrání sample s error handlingem."""
        try:
            logger.debug(f"Playing sample: {sample.filename}")
            self.audio_player.stop_playback()
            QTimer.singleShot(50, lambda: self.audio_player.play_sample(sample))
        except Exception as e:
            logger.error(f"Chyba při přehrávání {sample.filename}: {e}")

    def safe_stop_audio(self):
        """Bezpečné zastavení audio."""
        try:
            self.audio_player.stop_playback()
        except Exception as e:
            logger.error(f"Chyba při zastavování audio: {e}")

    def load_samples(self, input_folder: Path):
        """Načte samples ze složky a spustí analýzu."""
        self.status_panel.show_progress()
        self.status_panel.update_progress(0, "Analýza zahájena...")

        # Použij FixedBatchAnalyzer
        self.analyzer = FixedBatchAnalyzer(input_folder)
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

        self.sample_list.update_samples(self.samples)
        self.mapping_matrix.clear_matrix()

        self.status_panel.update_status(f"Analýza dokončena. {len(self.samples)} samples načteno.")

    def set_output_folder(self, output_folder: Path):
        """Nastaví výstupní složku."""
        self.export_manager = ExportManager(output_folder)
        if self.export_manager.validate_export_folder():
            self.status_panel.update_status(f"Výstupní složka nastavena: {output_folder.name}")
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
        """NOVÝ ASYNCHRONNÍ EXPORT s progress barem."""
        if not self.export_manager:
            QMessageBox.warning(self, "Chyba", "Není vybrána výstupní složka")
            return

        if not self.mapping_matrix.mapping:
            QMessageBox.warning(self, "Chyba", "Žádné samples nejsou namapované")
            return

        try:
            # Spusti asynchronní export
            self.export_thread = ExportThread(
                mapping=self.mapping_matrix.mapping,
                output_folder=self.export_manager.output_folder
            )

            # Připoj signály
            self.export_thread.progress_updated.connect(self.status_panel.update_progress)
            self.export_thread.export_completed.connect(self._on_export_completed)
            self.export_thread.export_failed.connect(self._on_export_failed)

            # UI změny
            self.control_panel.set_export_mode(True)
            self.status_panel.show_progress()

            # Spusti thread
            self.export_thread.start()
            logger.info("Export thread started")

        except Exception as e:
            logger.error(f"Failed to start export: {e}")
            QMessageBox.critical(self, "Chyba exportu", f"Nelze spustit export:\n{e}")

    def cancel_export(self):
        """Zruší probíhající export."""
        if self.export_thread and self.export_thread.isRunning():
            self.export_thread.cancel_export()
            self.export_thread.wait(3000)  # Čekej max 3 sekundy

            self.control_panel.set_export_mode(False)
            self.status_panel.hide_progress()
            self.status_panel.update_status("Export zrušen")

            logger.info("Export cancelled by user")

    def _on_export_completed(self, export_info: dict):
        """Handler pro dokončení exportu."""
        self.control_panel.set_export_mode(False)
        self.status_panel.hide_progress()

        # Zobraz výsledky
        message = (f"Export úspěšně dokončen!\n\n"
                   f"✓ Exportováno: {export_info['exported_count']} samples\n"
                   f"✓ Celkem souborů: {export_info['total_files']}\n"
                   f"📁 Složka: {self.export_manager.output_folder}")

        if export_info['failed_count'] > 0:
            message += f"\n\n⚠️ Chyby: {export_info['failed_count']} samples"

            # Zobraz detaily chyb v separátním dialogu
            failed_details = "\n".join([f"• {name}: {error}" for name, error in export_info['failed_files'][:10]])
            if len(export_info['failed_files']) > 10:
                failed_details += f"\n... a {len(export_info['failed_files']) - 10} dalších"

            QMessageBox.warning(self, "Export s chybami", message + f"\n\nDetaily chyb:\n{failed_details}")
        else:
            QMessageBox.information(self, "Export dokončen", message)

        self.status_panel.update_status(f"Export dokončen: {export_info['exported_count']} samples")

    def _on_export_failed(self, error_message: str):
        """Handler pro selhání exportu."""
        self.control_panel.set_export_mode(False)
        self.status_panel.hide_progress()
        self.status_panel.update_status("Export selhal")

        QMessageBox.critical(self, "Chyba exportu", f"Export selhal:\n\n{error_message}")
        logger.error(f"Export failed: {error_message}")

    def _on_sample_selected(self, sample: SampleMetadata):
        """Handler pro výběr sample."""
        logger.debug(f"Sample selected: {sample.filename}")
        self.mapping_matrix.highlight_sample_in_matrix(sample)

    def _on_sample_mapped(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """Handler pro mapování sample."""
        self.sample_list.refresh_display()
        self.update_export_button_state()

    def _on_sample_unmapped(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """Handler pro unmapování sample."""
        self.sample_list.refresh_display()
        self.update_export_button_state()

    def _on_sample_moved(self, sample: SampleMetadata, old_midi: int, old_velocity: int, new_midi: int, new_velocity: int):
        """Handler pro přesun sample."""
        self.sample_list.refresh_display()

    def _on_midi_note_changed(self, sample: SampleMetadata, old_midi: int, new_midi: int):
        """Handler pro změnu MIDI noty z inline editoru."""
        logger.debug(f"MIDI changed for {sample.filename}: {old_midi} -> {new_midi}")

        # Aktualizuj v matici pokud je mapovaný
        cell = self.mapping_matrix.find_cell_by_sample(sample)
        if cell:
            # Přesuň sample v matici
            self.mapping_matrix.remove_sample(old_midi, cell.velocity)
            self.mapping_matrix.add_sample(sample, new_midi, cell.velocity)
            logger.info(f"Moved {sample.filename} in matrix from MIDI {old_midi} to {new_midi}")

    def closeEvent(self, event):
        """Handler pro zavření aplikace."""
        # Zastaví probíhající export
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

        # Zobraz tip při spuštění
        from audio_player import AUDIO_AVAILABLE

        audio_status = "✓ Audio k dispozici" if AUDIO_AVAILABLE else "⚠️ Audio není k dispozici"

        QMessageBox.information(window, "Sampler Editor - S asynchronním exportem",
                                f"Sampler Editor - nyní s asynchronním exportem!\n\n"
                                f"Status: {audio_status}\n\n"
                                "NOVÉ FUNKCE:\n"
                                "• Asynchronní export s progress barem\n"
                                "• Možnost zrušení probíhajícího exportu\n"
                                "• Detailní feedback o exportovaných souborech\n"
                                "• Neblokující UI během exportu\n\n"
                                "ZACHOVANÉ FUNKCE:\n"
                                "• Dedikovaná drag tlačítka (⋮⋮)\n"
                                "• Center-based auto-assign algoritmus\n"
                                "• Skutečná sample rate konverze\n"
                                "• Stabilní selection v sample listu\n\n"
                                "OVLÁDÁNÍ:\n"
                                "• Export nyní zobrazuje progress a lze jej zrušit\n"
                                "• Během exportu jsou ostatní operace zakázány\n"
                                "• Detailní zprávy o tom, co se právě exportuje\n\n"
                                "Workflow:\n"
                                "1. Vyberte vstupní složku → CREPE analýza\n"
                                "2. Upravte MIDI noty inline editory\n"
                                "3. Mapování pomocí drag tlačítek (⋮⋮)\n"
                                "4. Export s progress barem a možností zrušení")

        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"Chyba aplikace: {e}", exc_info=True)
        QMessageBox.critical(None, "Kritická chyba", f"Aplikace selhala:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()