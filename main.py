"""
main.py - Finální konsolidovaná verze Sampler Editoru s nejnovějšími komponenty
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

# Import nejnovějších komponent
from drag_drop_components import DragDropMappingMatrix, DragDropSampleList  # z v2 verze
from audio_player import AudioPlayer  # z v3 verze
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

    def enable_export(self, enabled: bool):
        """Povolí/zakáže export button."""
        self.btn_export.setEnabled(enabled)


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
    """Hlavní okno aplikace s nejnovějšími komponenty."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sampler Editor - Finální verze s Inline MIDI Editorem")
        self.resize(1600, 900)  # Širší pro inline editory

        self.samples = []
        self.export_manager = None

        # Audio player z v3
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

        # Levý sloupec: Sample list s inline editorem (30%)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(2, 2, 2, 2)

        self.sample_list = DragDropSampleList()  # z v2 verze s inline editorem
        self.sample_list.setMinimumWidth(300)
        self.sample_list.setMaximumWidth(600)
        left_layout.addWidget(self.sample_list)

        splitter.addWidget(left_widget)

        # Pravý sloupec: Mapping matrix + Audio player (70%)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(2, 2, 2, 2)

        self.mapping_matrix = DragDropMappingMatrix()  # z v2 verze s vylepšeními
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
        splitter.setStretchFactor(0, 3)  # Sample list má váhu 3
        splitter.setStretchFactor(1, 7)  # Matrix má váhu 7

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
            # Immediate stop před novým přehráváním
            self.audio_player.stop_playback()

            # Krátká pauza pro cleanup
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
        self.status_panel.progress_bar.setVisible(True)
        self.status_panel.progress_bar.setValue(0)
        self.status_panel.update_status("Analýza zahájena...")

        # Použij FixedBatchAnalyzer
        self.analyzer = FixedBatchAnalyzer(input_folder)
        self.analyzer.progress_updated.connect(self.status_panel.update_progress)
        self.analyzer.analysis_completed.connect(self._on_analysis_completed)
        self.analyzer.start()

    def _on_analysis_completed(self, samples: List[SampleMetadata], range_info: dict):
        """Handler pro dokončení analýzy."""
        self.samples = [s for s in samples if s is not None]
        self.status_panel.progress_bar.setVisible(False)

        if not self.samples:
            self.status_panel.update_status("Žádné validní samples nalezeny")
            return

        self.sample_list.update_samples(self.samples)
        self.mapping_matrix.clear_matrix()

        self.status_panel.update_status(f"Analýza dokončena. {len(self.samples)} samples načteno s inline MIDI editory.")

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
        """Export namapovaných samples."""
        if not self.export_manager:
            QMessageBox.warning(self, "Chyba", "Není vybrána výstupní složka")
            return

        if not self.mapping_matrix.mapping:
            QMessageBox.warning(self, "Chyba", "Žádné samples nejsou namapované")
            return

        try:
            # Validace před exportem
            errors = ExportValidator.validate_mapping(self.mapping_matrix.mapping)
            if errors:
                QMessageBox.warning(self, "Chyba validace", "Nalezeny chyby:\n\n" + "\n".join(errors[:5]))
                return

            # Export
            export_info = self.export_manager.export_mapped_samples(self.mapping_matrix.mapping)

            # Zobraz výsledky
            message = (f"Export úspěšně dokončen!\n\n"
                       f"✓ Exportováno: {export_info['exported_count']} samples\n"
                       f"✓ Celkem souborů: {export_info['total_files']}\n"
                       f"📁 Složka: {self.export_manager.output_folder}")

            if export_info['failed_count'] > 0:
                message += f"\n\n⚠️ Chyby: {export_info['failed_count']} samples"

            QMessageBox.information(self, "Export dokončen", message)

        except Exception as e:
            logger.error(f"Export failed: {e}")
            QMessageBox.critical(self, "Chyba exportu", f"Chyba při exportu:\n{e}")

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

        QMessageBox.information(window, "Sampler Editor - Finální verze",
                                f"Sampler Editor - konsolidovaná finální verze!\n\n"
                                f"Status: {audio_status}\n\n"
                                "FUNKCE:\n"
                                "• Inline MIDI editory u každého sample\n"
                                "• Transpozice ±1 půltón, ±12 půltónů (oktáva)\n"
                                "• Levý klik v matici = přehrát/odstranit\n"
                                "• Pravý klik v matici = odstranit\n"
                                "• Auto-assign tlačítka pro MIDI noty\n"
                                "• Play tlačítka pro MIDI tóny\n"
                                "• Stabilní audio přehrávání\n\n"
                                "OVLÁDÁNÍ:\n"
                                "• Inline editory: -12/-1/+1/+12 pro transpozici\n"
                                "• Klávesy v seznamu: MEZERNÍK/S/D/ESC/T\n"
                                "• Matrix: Levý klik = přehrát, Pravý klik = odstranit\n"
                                "• Zelená tlačítka ♪ = přehrát MIDI tón\n"
                                "• Oranžová tlačítka ⚡ = auto-assign podle RMS\n\n"
                                "Workflow:\n"
                                "1. Vyberte vstupní složku → CREPE analýza\n"
                                "2. Upravte MIDI noty inline editory\n"
                                "3. Mapování drag & drop do matice\n"
                                "4. Export s standardní konvencí")

        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"Chyba aplikace: {e}", exc_info=True)
        QMessageBox.critical(None, "Kritická chyba", f"Aplikace selhala:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()