"""
main.py - Hlavní aplikace Sampler Editor s drag & drop podporou a plynulým posouváním
"""

import sys
import logging
from pathlib import Path
from typing import List
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                               QWidget, QPushButton, QLabel, QFileDialog, QProgressBar,
                               QSplitter, QMessageBox, QGroupBox, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

# Import helper modulů
from models import SampleMetadata
from audio_analyzer import BatchAnalyzer
from midi_utils import MidiUtils, VelocityUtils
from export_utils import ExportManager, ExportValidator
from drag_drop_components import DragDropMappingMatrix, DragDropSampleList
from audio_player import AudioPlayer, AudioPlayerStatus
from sample_editor_widget import SampleMidiEditor

# Nastavení loggingu
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ControlPanel(QGroupBox):
    """Kontejner pro ovládací prvky (horní panel)"""

    input_folder_selected = Signal(Path)
    output_folder_selected = Signal(Path)
    export_requested = Signal()

    def __init__(self):
        super().__init__("Ovládání")
        self.input_folder = None
        self.output_folder = None
        self.init_ui()

    def init_ui(self):
        """Inicializace ovládacího panelu"""
        layout = QHBoxLayout()
        layout.setSpacing(15)

        # Vstupní složka - kompaktní
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
        separator1.setFrameShape(QFrame.VLine)
        separator1.setFrameShadow(QFrame.Sunken)
        separator1.setMaximumHeight(30)
        layout.addWidget(separator1)

        # Výstupní složka - kompaktní
        self.btn_output_folder = QPushButton("Výstupní složka...")
        self.btn_output_folder.clicked.connect(self.select_output_folder)
        self.btn_output_folder.setMaximumWidth(120)
        layout.addWidget(self.btn_output_folder)

        self.output_folder_label = QLabel("Žádná složka")
        self.output_folder_label.setStyleSheet("color: gray; font-style: italic; font-size: 12px;")
        self.output_folder_label.setMaximumWidth(150)
        layout.addWidget(self.output_folder_label)

        # Stretch pro oddělení od export buttonu
        layout.addStretch()

        # Export button
        self.btn_export = QPushButton("Export")
        self.btn_export.clicked.connect(self.export_samples)
        self.btn_export.setEnabled(False)
        self.btn_export.setMaximumWidth(80)
        self.btn_export.setStyleSheet("QPushButton:enabled { background-color: #4CAF50; color: white; font-weight: bold; }")
        layout.addWidget(self.btn_export)

        self.setLayout(layout)
        self.setMaximumHeight(60)  # Omezí výšku panelu

    def select_input_folder(self):
        """Výběr vstupní složky"""
        folder = QFileDialog.getExistingDirectory(self, "Vyberte složku se samples")
        if folder:
            self.input_folder = Path(folder)
            self.input_folder_label.setText(f"{self.input_folder.name}")
            self.input_folder_label.setStyleSheet("color: black; font-weight: bold; font-size: 12px;")
            self.input_folder_selected.emit(self.input_folder)

    def select_output_folder(self):
        """Výběr výstupní složky"""
        folder = QFileDialog.getExistingDirectory(self, "Vyberte výstupní složku")
        if folder:
            self.output_folder = Path(folder)
            self.output_folder_label.setText(f"{self.output_folder.name}")
            self.output_folder_label.setStyleSheet("color: black; font-weight: bold; font-size: 12px;")
            self.output_folder_selected.emit(self.output_folder)

    def export_samples(self):
        """Signál pro export"""
        self.export_requested.emit()

    def enable_export(self, enabled: bool):
        """Povolí/zakáže export button"""
        self.btn_export.setEnabled(enabled)


class StatusPanel(QGroupBox):
    """Kontejner pro status informace a progress"""

    def __init__(self):
        super().__init__("Status")
        self.init_ui()

    def init_ui(self):
        """Inicializace status panelu"""
        layout = QVBoxLayout()

        self.status_label = QLabel("Připraven. Vyberte vstupní složku se samples.")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)
        self.setMaximumHeight(100)

    def update_status(self, message: str):
        """Aktualizuje status zprávu"""
        self.status_label.setText(message)

    def update_progress(self, value: int, message: str = None):
        """Aktualizuje progress bar"""
        self.progress_bar.setValue(value)
        if message:
            self.status_label.setText(message)

    def show_progress(self, show: bool):
        """Zobrazí/skryje progress bar"""
        self.progress_bar.setVisible(show)


class MainWindow(QMainWindow):
    """Hlavní okno aplikace s drag & drop podporou a plynulým posouváním"""

    def __init__(self):
        super().__init__()
        self.samples = []
        self.analyzer = None
        self.export_manager = None

        # Audio přehrávač
        self.audio_player = AudioPlayer()
        self.audio_status = AudioPlayerStatus(self.audio_player)

        # Referenční přehrávač pro MIDI tóny
        from audio_player import ReferencePlayer
        self.reference_player = ReferencePlayer()

        self.init_ui()
        self.connect_signals()

        self.setWindowTitle("Sampler Editor - Prototype v0.7 (Plynulé posouvání + MIDI Editor)")
        self.setGeometry(100, 100, 1700, 1000)  # Větší okno pro MIDI editor

    def init_ui(self):
        """Inicializace uživatelského rozhraní"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Hlavní layout
        main_layout = QVBoxLayout()

        # Horní sekce - ovládání
        self.control_panel = ControlPanel()
        main_layout.addWidget(self.control_panel)

        # Status panel
        self.status_panel = StatusPanel()
        main_layout.addWidget(self.status_panel)

        # Hlavní sekce - splitter pro mapping matrix a sample list
        content_splitter = QSplitter(Qt.Horizontal)

        # Levá strana - mapovací matice
        self.mapping_matrix = DragDropMappingMatrix()
        content_splitter.addWidget(self.mapping_matrix)

        # Pravá strana - vertikální layout pro sample list a editor
        right_widget = QWidget()
        right_layout = QVBoxLayout()

        # MIDI editor pro vybraný sample
        self.sample_editor = SampleMidiEditor()
        right_layout.addWidget(self.sample_editor)

        # Seznam sampleů s drag podporou
        self.sample_list = DragDropSampleList()
        right_layout.addWidget(self.sample_list)

        right_widget.setLayout(right_layout)
        content_splitter.addWidget(right_widget)

        # Nastavení poměru spliteru (70% matice, 30% pravá strana)
        content_splitter.setSizes([1100, 500])
        main_layout.addWidget(content_splitter)

        central_widget.setLayout(main_layout)

    def keyPressEvent(self, event):
        """Obsluha klávesových zkratek na úrovni hlavního okna"""
        if event.key() == Qt.Key_Escape:
            # ESC - zastaví přehrávání
            if self.audio_player.is_playing or self.audio_player.is_comparing:
                self.audio_player.stop_playback()
                event.accept()
                return

        super().keyPressEvent(event)

    def connect_signals(self):
        """Propojení signálů mezi komponenty"""
        # Control panel signals
        self.control_panel.input_folder_selected.connect(self.on_input_folder_selected)
        self.control_panel.output_folder_selected.connect(self.on_output_folder_selected)
        self.control_panel.export_requested.connect(self.export_samples)

        # Sample list signals
        self.sample_list.sample_selected.connect(self.on_sample_selected)
        self.sample_list.play_requested.connect(self.on_play_requested)
        self.sample_list.compare_requested.connect(self.on_compare_requested)
        self.sample_list.simultaneous_requested.connect(self.on_simultaneous_requested)

        # MIDI editor signals
        self.sample_editor.midi_note_changed.connect(self.on_midi_note_changed)
        # Zkontrolujte, jestli SampleMidiEditor má signál play_transposed_tone
        if hasattr(self.sample_editor, 'play_transposed_tone'):
            self.sample_editor.play_transposed_tone.connect(self.on_play_transposed_tone)  # NOVÝ SIGNÁL

        # Mapping matrix signals - drag & drop, přehrávání a MIDI tóny
        self.mapping_matrix.sample_mapped.connect(self.on_sample_mapped)
        self.mapping_matrix.sample_unmapped.connect(self.on_sample_unmapped)
        self.mapping_matrix.sample_play_requested.connect(self.on_matrix_play_requested)
        self.mapping_matrix.midi_note_play_requested.connect(self.on_midi_note_play_requested)
        self.mapping_matrix.sample_moved.connect(self.on_sample_moved)  # NOVÝ SIGNÁL

        # Audio player signals
        self.audio_player.playback_started.connect(self.on_playback_started)
        self.audio_player.playback_stopped.connect(self.on_playback_stopped)
        self.audio_player.playback_error.connect(self.on_playback_error)
        self.audio_player.compare_started.connect(self.on_compare_started)

    def on_input_folder_selected(self, folder: Path):
        """Obsluha výběru vstupní složky"""
        self.status_panel.update_status("Spouštím analýzu sampleů...")
        self.start_batch_analysis(folder)

    def on_output_folder_selected(self, folder: Path):
        """Obsluha výběru výstupní složky"""
        self.export_manager = ExportManager(folder)
        self.status_panel.update_status(f"Výstupní složka nastavena: {folder.name}")
        self.update_export_button_state()

    def on_sample_selected(self, sample: SampleMetadata):
        """Obsluha výběru sample ze seznamu"""
        # Nastav sample jako aktuální pro přehrávání
        self.audio_player.set_current_sample(sample)

        # Nastav sample v MIDI editoru
        self.sample_editor.set_current_sample(sample)

        # Pokud je sample namapovaný, posun matici na jeho pozici
        if sample.mapped:
            self.mapping_matrix.scroll_to_sample(sample)

        note_name = MidiUtils.midi_to_note_name(sample.detected_midi)
        velocity_desc = VelocityUtils.velocity_to_description(sample.velocity_level)

        status_msg = f"Vybrán sample: {sample.filename} | {note_name} | {velocity_desc}"
        if sample.mapped:
            status_msg += " | ✓ Namapován (matice posunuta na pozici)"
        else:
            status_msg += " | Přetáhněte do matice"
        status_msg += " | MEZERNÍK = přehrát | S = porovnat"

        self.status_panel.update_status(status_msg)

    def on_play_requested(self, sample: SampleMetadata):
        """Obsluha požadavku na přehrání sample (mezerník)"""
        self.audio_player.play_sample(sample)

    def on_compare_requested(self, sample: SampleMetadata):
        """Obsluha požadavku na srovnávací přehrávání (S klávesa)"""
        self.audio_player.compare_sample(sample)

    def on_simultaneous_requested(self, sample: SampleMetadata):
        """Obsluha požadavku na současné přehrávání (D klávesa)"""
        self.audio_player.compare_sample_simultaneous(sample)

    def on_matrix_play_requested(self, sample: SampleMetadata):
        """Obsluha přehrávání sample z mapovací matice (klik na buňku)"""
        self.audio_player.play_sample(sample)

        note_name = MidiUtils.midi_to_note_name(sample.detected_midi)
        self.status_panel.update_status(f"▶ Přehrává z matice: {sample.filename} ({note_name})")

    def on_midi_note_play_requested(self, midi_note: int):
        """Obsluha přehrávání MIDI tónu (klik na MIDI číslo)"""
        self.reference_player.play_midi_note(midi_note, duration=1.5)
        note_name = MidiUtils.midi_to_note_name(midi_note)
        self.status_panel.update_status(f"🎵 Přehrává MIDI tón: {note_name} (MIDI {midi_note})")

    def on_play_transposed_tone(self, midi_note: int):
        """Obsluha přehrávání transponovaného MIDI tónu z editoru"""
        self.reference_player.play_midi_note(midi_note, duration=1.0)
        note_name = MidiUtils.midi_to_note_name(midi_note)
        self.status_panel.update_status(f"🎵 Transponovaný tón: {note_name} (MIDI {midi_note})")

    def on_midi_note_changed(self, sample: SampleMetadata, old_midi: int, new_midi: int):
        """Obsluha změny MIDI noty v editoru"""
        old_note = MidiUtils.midi_to_note_name(old_midi)
        new_note = MidiUtils.midi_to_note_name(new_midi)

        # Aktualizuj zobrazení v sample listu
        self.sample_list.update_samples(self.samples)

        # Pokud je sample namapovaný, odmapuj ho (bude potřeba přemapovat)
        if sample.mapped:
            sample.mapped = False
            # Najdi a odstraň z mapování
            keys_to_remove = []
            for key, mapped_sample in self.mapping_matrix.mapping.items():
                if mapped_sample == sample:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self.mapping_matrix.mapping[key]
                # Aktualizuj buňku v matici pokud je zobrazená
                if key in self.mapping_matrix.matrix_cells:
                    cell = self.mapping_matrix.matrix_cells[key]
                    cell.sample = None
                    cell._update_style()

            self.mapping_matrix._update_stats()
            self.sample_list.refresh_display()

        self.status_panel.update_status(
            f"MIDI nota změněna: {sample.filename} | {old_note} → {new_note} | "
            f"Přemapujte sample do matice"
        )

        logger.info(f"MIDI nota změněna: {sample.filename} | MIDI {old_midi} → {new_midi}")

    def on_sample_moved(self, sample: SampleMetadata, old_midi: int, old_velocity: int, new_midi: int, new_velocity: int):
        """Obsluha přesunu sample v mapovací matici"""
        old_note = MidiUtils.midi_to_note_name(old_midi)
        new_note = MidiUtils.midi_to_note_name(new_midi)

        # Aktualizuj zobrazení v sample listu (nemusí se měnit, ale pro jistotu)
        self.sample_list.refresh_display()

        # Aktualizuj export button state
        self.update_export_button_state()

        # Zobraz informaci o přesunu
        self.status_panel.update_status(
            f"✓ Sample {sample.filename} přesunut: "
            f"{old_note} (V{old_velocity}) → {new_note} (V{new_velocity})"
        )

        logger.info(f"Sample moved: {sample.filename} | "
                   f"MIDI {old_midi}:V{old_velocity} → MIDI {new_midi}:V{new_velocity}")

    def on_compare_started(self, message: str):
        """Obsluha spuštění srovnávacího přehrávání"""
        self.status_panel.update_status(f"🔊 Srovnávací přehrávání: {message}")

    def on_playback_started(self, filename: str):
        """Obsluha spuštění přehrávání"""
        self.status_panel.update_status(f"▶ Přehrává: {filename} | ESC = zastavit")

    def on_playback_stopped(self):
        """Obsluha zastavení přehrávání"""
        self.status_panel.update_status("⏹ Přehrávání dokončeno")

    def on_playback_error(self, error: str):
        """Obsluha chyby přehrávání"""
        self.status_panel.update_status(f"❌ Chyba přehrávání: {error}")
        QMessageBox.warning(self, "Chyba přehrávání", error)

    def on_sample_mapped(self, sample: SampleMetadata, midi: int, velocity: int):
        """Obsluha namapování sample přes drag & drop"""
        self.sample_list.refresh_display()
        self.update_export_button_state()

        note_name = MidiUtils.midi_to_note_name(midi)
        velocity_desc = VelocityUtils.velocity_to_description(velocity)

        self.status_panel.update_status(
            f"✓ Sample {sample.filename} namapován na {note_name} ({velocity_desc})"
        )

        logger.info(f"Drag & Drop: {sample.filename} -> MIDI {midi}, Velocity {velocity}")

    def on_sample_unmapped(self, sample: SampleMetadata, midi: int, velocity: int):
        """Obsluha odmapování sample (při přepsání)"""
        self.sample_list.refresh_display()

        note_name = MidiUtils.midi_to_note_name(midi)
        logger.info(f"Sample {sample.filename} odmapován z {note_name}")

    def start_batch_analysis(self, folder: Path):
        """Spustí batch analýzu"""
        self.status_panel.show_progress(True)
        self.status_panel.update_progress(0)

        self.analyzer = BatchAnalyzer(folder)
        self.analyzer.progress_updated.connect(self.status_panel.update_progress)
        self.analyzer.analysis_completed.connect(self.on_analysis_completed)
        self.analyzer.start()

    def on_analysis_completed(self, samples: List[SampleMetadata]):
        """Obsluha dokončení analýzy"""
        self.samples = samples
        self.status_panel.show_progress(False)

        if samples:
            self.status_panel.update_status(
                f"Analýza dokončena. Načteno {len(samples)} sampleů. "
                f"Celý piano rozsah A0-C8 je dostupný pro mapování."
            )
            self.sample_list.update_samples(samples)

            # Auto-mapping jen několika sampleů pro demonstraci
            self.auto_map_samples()
        else:
            self.status_panel.update_status("Žádné samples nenalezeny nebo analýza selhala.")

        self.update_export_button_state()

    def auto_map_samples(self):
        """Automatické mapování prvních několika sampleů pro demonstraci"""
        mapped_count = 0

        # Namapuj jen 5 sampleů automaticky kolem jejich detekovaných pozic
        for sample in self.samples[:5]:
            if sample.analyzed and not sample.mapped:
                # Použij detekovanou MIDI notu
                target_midi = sample.detected_midi
                velocity = min(sample.velocity_level, 7)

                # Zkontroluj, jestli místo není obsazené
                key = (target_midi, velocity)
                if key not in self.mapping_matrix.mapping:
                    self.mapping_matrix.add_sample(sample, target_midi, velocity)
                    mapped_count += 1

        if mapped_count > 0:
            self.status_panel.update_status(
                f"Auto-mapováno {mapped_count} sampleů na jejich detekované pozice. "
                f"Použijte scroll pro navigaci celým piano rozsahem."
            )

    def update_export_button_state(self):
        """Aktualizuje stav export buttonu"""
        has_output = self.export_manager is not None
        has_mapped = len(self.mapping_matrix.get_mapped_samples()) > 0
        self.control_panel.enable_export(has_output and has_mapped)

    def export_samples(self):
        """Export namapovaných sampleů"""
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
                QMessageBox.warning(self, "Chyba validace",
                                   "Nalezeny chyby v mapování:\n\n" + "\n".join(errors[:5]))
                return

            # Kontrola konfliktů
            conflicts = ExportValidator.check_filename_conflicts(self.mapping_matrix.mapping)
            if conflicts:
                QMessageBox.warning(self, "Konflikty názvů",
                                   "Nalezeny konflikty v názvech souborů:\n\n" + "\n".join(conflicts[:3]))
                return

            # Export
            export_info = self.export_manager.export_mapped_samples(self.mapping_matrix.mapping)

            # Zobraz výsledky
            message = (f"Export úspěšně dokončen!\n\n"
                      f"✓ Exportováno: {export_info['exported_count']} sampleů\n"
                      f"✓ Celkem souborů: {export_info['total_files']}\n"
                      f"📁 Složka: {self.export_manager.output_folder}")

            if export_info['failed_count'] > 0:
                message += f"\n\n⚠️ Chyby: {export_info['failed_count']} sampleů"
                message += f"\nDetails: {', '.join([f[0] for f in export_info['failed_files'][:3]])}"

            QMessageBox.information(self, "Export dokončen", message)

            self.status_panel.update_status(
                f"✓ Export dokončen: {export_info['exported_count']} sampleů, "
                f"{export_info['total_files']} souborů"
            )

        except Exception as e:
            QMessageBox.critical(self, "Chyba exportu", f"Neočekávaná chyba při exportu:\n{e}")
            logger.error(f"Export error: {e}", exc_info=True)


def main():
    """Hlavní funkce aplikace"""
    app = QApplication(sys.argv)

    app.setApplicationName("Sampler Editor Prototype")
    app.setApplicationVersion("0.7.0")

    try:
        window = MainWindow()
        window.show()

        # Zobraz tip při spuštění
        from audio_player import AUDIO_AVAILABLE

        audio_status = "✓ Audio k dispozici" if AUDIO_AVAILABLE else "⚠️ Audio není k dispozici"

        QMessageBox.information(window, "Sampler Editor - S automatickým přehráváním transponovaných tónů",
                               f"Sampler Editor - celý piano rozsah + auto-přehrávání při transpozici!\n\n"
                               f"Status: {audio_status}\n\n"
                               "Klíčové funkce:\n"
                               "• Celý piano rozsah A0-C8 (88 kláves) v jednom zobrazení\n"
                               "• Nejvyšší frekvence (C8) nahoře, nejnižší (A0) dole\n"
                               "• Automatické přehrávání tónu při transpozici\n"
                               "• Kontrola auto-přehrávání (ZAP/VYP)\n"
                               "• Vertikální scrollování pro navigaci\n"
                               "• Přetahování samples mezi pozicemi v matici\n\n"
                               "MIDI Editor:\n"
                               "• +/- = ±1 půltón s auto-přehráním\n"
                               "• +12/-12 = ±1 oktáva s auto-přehráním\n"
                               "• Přímý vstup MIDI čísla ve spinboxu\n"
                               "• Tlačítko pro manuální přehrání tónu\n"
                               "• Auto-přehrávání lze vypnout/zapnout\n\n"
                               "Jak používat:\n"
                               "1. Vyberte vstupní složku se samples\n"
                               "2. Počkejte na analýzu\n"
                               "3. Označte sample v seznamu\n"
                               "4. Upravte MIDI notu tlačítky → automaticky se přehraje nový tón\n"
                               "5. Testujte zvuk různými způsoby\n"
                               "6. Přetáhněte samples do mapovací matice\n"
                               "7. Použijte scroll pro navigaci po celém piano\n"
                               "8. Klikněte na MIDI čísla pro referenční tóny\n"
                               "9. Klikněte na buňky pro přehrání sampleů\n"
                               "10. Exportujte s kompletní konvencí názvů\n\n"
                               "Klávesové zkratky (v seznamu):\n"
                               "• MEZERNÍK = přehrát sample\n"
                               "• S = srovnávací (tón → pauza → sample)\n"
                               "• D = současné (tón + sample mix)\n"
                               "• ESC = zastavit přehrávání\n\n"
                               "Mapovací matice:\n"
                               "• Levý klik MIDI čísla = referenční tón\n"
                               "• Levý klik buňky = přehrát sample\n"
                               "• Pravý klik buňky = zobrazit info\n"
                               "• Tažení buňky = přesun sample\n\n"
                               "Export: Kompletní konvence mXXX-velY-fZZ.wav")

        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"Chyba při spuštění aplikace: {e}", exc_info=True)
        QMessageBox.critical(None, "Kritická chyba",
                           f"Aplikace se nepodařilo spustit:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()