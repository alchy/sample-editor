"""
main.py - Hlavní aplikace Sampler Editor s pitch/amplitude detekcí a obousměrnou synchronizací výběru
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
from models import SampleMetadata, AmplitudeFilterSettings
from audio_analyzer import BatchAnalyzer
from midi_utils import MidiUtils, VelocityUtils
from export_utils import ExportManager, ExportValidator
from drag_drop_components import DragDropMappingMatrix, DragDropSampleList
from audio_player import AudioPlayer, AudioPlayerStatus
from sample_editor_widget import SampleMidiEditor
from amplitude_filter_widget import AmplitudeFilterWidget
from amplitude_analyzer import AmplitudeRangeManager

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
        self.btn_export.setStyleSheet(
            "QPushButton:enabled { background-color: #4CAF50; color: white; font-weight: bold; }")
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
    """Kontejner pro status informace - pouze levá polovina"""

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
    """Hlavní okno aplikace s pitch/amplitude detekcí a obousměrnou synchronizací výběru"""

    def __init__(self):
        super().__init__()
        self.samples = []
        self.analyzer = None
        self.export_manager = None
        self.amplitude_range_manager = AmplitudeRangeManager()

        # Audio přehrávač
        self.audio_player = AudioPlayer()
        self.audio_status = AudioPlayerStatus(self.audio_player)

        # Referenční přehrávač pro MIDI tóny
        from audio_player import ReferencePlayer
        self.reference_player = ReferencePlayer()

        self.init_ui()
        self.connect_signals()

        self.setWindowTitle("Sampler Editor - v0.8 (CREPE Pitch + Velocity Amplitude Detection + Selection Sync)")
        self.setGeometry(100, 100, 1700, 1000)

    def init_ui(self):
        """Inicializace uživatelského rozhraní"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Hlavní layout
        main_layout = QVBoxLayout()

        # Horní sekce - ovládání
        self.control_panel = ControlPanel()
        main_layout.addWidget(self.control_panel)

        # Status a amplitude filter - horizontální rozdělení
        status_layout = QHBoxLayout()

        # Levá polovina - status panel
        self.status_panel = StatusPanel()
        status_layout.addWidget(self.status_panel)

        # Pravá polovina - amplitude filter
        self.amplitude_filter = AmplitudeFilterWidget()
        status_layout.addWidget(self.amplitude_filter)

        main_layout.addLayout(status_layout)

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

        # Seznam samples s drag podporou
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
        """Propojení signálů mezi komponenty - rozšířeno o obousměrnou synchronizaci"""
        # Control panel signals
        self.control_panel.input_folder_selected.connect(self.on_input_folder_selected)
        self.control_panel.output_folder_selected.connect(self.on_output_folder_selected)
        self.control_panel.export_requested.connect(self.export_samples)

        # Amplitude filter signals
        self.amplitude_filter.filter_applied.connect(self.on_amplitude_filter_applied)
        self.amplitude_filter.velocity_assigned.connect(self.on_velocity_assigned)

        # Sample list signals
        self.sample_list.sample_selected.connect(self.on_sample_selected)
        self.sample_list.play_requested.connect(self.on_play_requested)
        self.sample_list.compare_requested.connect(self.on_compare_requested)
        self.sample_list.simultaneous_requested.connect(self.on_simultaneous_requested)

        # MIDI editor signals
        self.sample_editor.midi_note_changed.connect(self.on_midi_note_changed)
        if hasattr(self.sample_editor, 'play_transposed_tone'):
            self.sample_editor.play_transposed_tone.connect(self.on_play_transposed_tone)

        # Mapping matrix signals - drag & drop, přehrávání a MIDI tóny
        self.mapping_matrix.sample_mapped.connect(self.on_sample_mapped)
        self.mapping_matrix.sample_unmapped.connect(self.on_sample_unmapped)
        self.mapping_matrix.sample_play_requested.connect(self.on_matrix_play_requested)
        self.mapping_matrix.midi_note_play_requested.connect(self.on_midi_note_play_requested)
        self.mapping_matrix.sample_moved.connect(self.on_sample_moved)

        # NOVÝ: Synchronizace výběru matrix → sample list
        self.mapping_matrix.sample_selected_in_matrix.connect(self.on_sample_selected_in_matrix)

        # Audio player signals
        self.audio_player.playback_started.connect(self.on_playback_started)
        self.audio_player.playback_stopped.connect(self.on_playback_stopped)
        self.audio_player.playback_error.connect(self.on_playback_error)
        self.audio_player.compare_started.connect(self.on_compare_started)

    def on_input_folder_selected(self, folder: Path):
        """Obsluha výběru vstupní složky"""
        self.status_panel.update_status("Spouštím analýzu samples s CREPE pitch a velocity amplitude detekcí...")
        self.start_batch_analysis(folder)

    def on_output_folder_selected(self, folder: Path):
        """Obsluha výběru výstupní složky"""
        self.export_manager = ExportManager(folder)
        self.status_panel.update_status(f"Výstupní složka nastavena: {folder.name}")
        self.update_export_button_state()

    def on_amplitude_filter_applied(self, filter_settings: AmplitudeFilterSettings):
        """Obsluha aplikace amplitude filtru - ZMĚNA: používá velocity_amplitude"""
        # Označit samples mimo rozsah šedou barvou
        filtered_count = 0
        for sample in self.samples:
            # ZMĚNA: kontrola velocity_amplitude místo peak_amplitude
            if sample.velocity_amplitude is not None:
                sample.is_filtered = not filter_settings.is_in_range(sample.velocity_amplitude)
                if sample.is_filtered:
                    filtered_count += 1
                    # Odmapuj filtrované samples
                    if sample.mapped:
                        sample.mapped = False
                        # Odstraň z mapping matrix
                        self._remove_sample_from_matrix(sample)

        # Aktualizuj zobrazení
        self.sample_list.refresh_display()
        self.mapping_matrix._update_stats()

        self.status_panel.update_status(
            f"✓ Velocity amplitude filter aplikován: {filtered_count} samples filtrováno"
        )

    def _find_best_frequency_position(self, sample: SampleMetadata, preferred_velocity: int,
                                      max_semitone_distance: int = 6) -> tuple:
        """
        Najde nejlepší dostupnou pozici podle MIDI metadata a frekvence

        Args:
            sample: Sample s MIDI metadata a frekvencí
            preferred_velocity: Preferovaný velocity level
            max_semitone_distance: Maximální vzdálenost v půltónech

        Returns:
            (midi_note, velocity) nebo None pokud není dostupná pozice
        """
        # Použij MIDI z metadata (z MIDI editoru) nebo detekovanou MIDI notu
        target_midi = sample.detected_midi
        target_frequency = sample.detected_frequency

        if target_midi is None or target_frequency is None:
            return None

        # Spočítej target frekvenci pro MIDI metadata
        metadata_frequency = 440.0 * (2 ** ((target_midi - 69) / 12))

        # Vygeneruj kandidáty kolem MIDI metadata
        candidates = []

        # Prohledej rozsah kolem target MIDI noty
        search_range = range(
            max(21, target_midi - max_semitone_distance),
            min(109, target_midi + max_semitone_distance + 1)
        )

        for midi_note in search_range:
            # Spočítej frekvenci pro kandidátskou MIDI notu
            note_frequency = 440.0 * (2 ** ((midi_note - 69) / 12))

            # Spočítej vzdálenosti
            midi_distance = abs(target_midi - midi_note)  # V půltónech
            freq_distance = abs(target_frequency - note_frequency)  # V Hz

            # Zkus různé velocity levels (preferovaný první)
            velocity_priorities = self._get_velocity_priority_list(preferred_velocity)

            for velocity in velocity_priorities:
                key = (midi_note, velocity)

                # Kontrola, zda je pozice volná nebo má stejnou frekvenci v range
                existing_sample = self.mapping_matrix.mapping.get(key)
                position_available = self._is_position_suitable(
                    key, existing_sample, target_frequency, sample
                )

                if position_available:
                    # Spočítej celkový score (menší = lepší)
                    # Prioritizuj MIDI přesnost nad frekvenční
                    midi_penalty = midi_distance * 2.0  # MIDI vzdálenost má vyšší váhu
                    freq_penalty = freq_distance * 0.01  # Frekvenční rozdíl má menší váhu
                    velocity_penalty = abs(velocity - preferred_velocity) * 0.5

                    score = midi_penalty + freq_penalty + velocity_penalty

                    candidates.append({
                        'midi': midi_note,
                        'velocity': velocity,
                        'midi_distance': midi_distance,
                        'freq_distance': freq_distance,
                        'velocity_distance': abs(velocity - preferred_velocity),
                        'score': score,
                        'has_existing': existing_sample is not None
                    })

        if not candidates:
            return None

        # Seřaď podle score (nejlepší první)
        candidates.sort(key=lambda x: x['score'])

        best = candidates[0]

        # Log pro debugging
        note_name = MidiUtils.midi_to_note_name(best['midi'])
        logger.debug(f"Best position for {sample.filename} (MIDI {target_midi}): "
                     f"{note_name} (MIDI {best['midi']}) V{best['velocity']}, "
                     f"midi_dist: {best['midi_distance']}, freq_dist: {best['freq_distance']:.1f}Hz")

        return (best['midi'], best['velocity'])

    def _get_velocity_priority_list(self, preferred_velocity: int) -> list:
        """Vrátí seznam velocity priorit (preferovaný první)"""
        priorities = [preferred_velocity]

        # Přidej blízké velocity levels
        for offset in [1, -1, 2, -2, 3, -3, 4, -4]:
            vel = preferred_velocity + offset
            if 0 <= vel <= 7 and vel not in priorities:
                priorities.append(vel)

        return priorities

    def _is_position_suitable(self, key: tuple, existing_sample, target_frequency: float,
                              new_sample) -> bool:
        """
        Kontroluje, zda je pozice vhodná pro přiřazení

        Args:
            key: (midi, velocity) pozice
            existing_sample: Existující sample na pozici nebo None
            target_frequency: Cílová frekvence nového sample
            new_sample: Nový sample k přiřazení

        Returns:
            True pokud je pozice dostupná nebo vhodná pro sdílení
        """
        if existing_sample is None:
            return True  # Pozice je volná

        # Pokud je pozice obsazená, zkontroluj kompatibilitu
        if existing_sample.detected_frequency is None:
            return False  # Existující sample nemá frekvenci

        # Povolí sdílení pozice pokud jsou frekvence blízké (v range)
        freq_tolerance = 20.0  # Hz tolerance pro sdílení pozice
        freq_diff = abs(target_frequency - existing_sample.detected_frequency)

        if freq_diff <= freq_tolerance:
            logger.debug(f"Position sharing: {new_sample.filename} can share position with "
                         f"{existing_sample.filename} (freq diff: {freq_diff:.1f}Hz)")
            return True

        return False  # Frekvence jsou příliš odlišné

    def on_velocity_assigned(self, filter_settings: AmplitudeFilterSettings):
        """Obsluha přiřazení velocity levels - ZMĚNA: používá velocity_amplitude"""
        assigned_count = 0
        auto_mapped_count = 0
        shared_positions = 0

        for sample in self.samples:
            # ZMĚNA: kontrola velocity_amplitude místo peak_amplitude
            if sample.velocity_amplitude is not None and not sample.is_filtered:
                old_velocity = sample.velocity_level
                # ZMĚNA: použití velocity_amplitude pro get_velocity_level
                new_velocity = filter_settings.get_velocity_level(sample.velocity_amplitude)

                if new_velocity >= 0:  # Validní velocity
                    sample.velocity_level = new_velocity
                    assigned_count += 1

                    # Pokud se velocity změnila a sample je namapovaný, odmapuj ho
                    if (old_velocity != new_velocity and sample.mapped):
                        sample.mapped = False
                        self._remove_sample_from_matrix(sample)

                    # SMART AUTO-ASSIGN: Přiřazení podle MIDI metadata a frekvence
                    if (sample.detected_midi is not None and
                            not sample.mapped and
                            sample.velocity_level is not None):

                        best_position = self._find_best_frequency_position(
                            sample,
                            sample.velocity_level
                        )

                        if best_position:
                            target_midi, target_velocity = best_position

                            # Kontrola na sdílení pozice
                            key = (target_midi, target_velocity)
                            if key in self.mapping_matrix.mapping:
                                shared_positions += 1
                                logger.info(
                                    f"Sharing position {MidiUtils.midi_to_note_name(target_midi)} V{target_velocity}: "
                                    f"{self.mapping_matrix.mapping[key].filename} + {sample.filename}")

                            self.mapping_matrix.add_sample(sample, target_midi, target_velocity)
                            auto_mapped_count += 1

        # Aktualizuj zobrazení
        self.sample_list.refresh_display()
        self.mapping_matrix._update_stats()

        status_msg = f"✓ Velocity assigned (RMS 500ms): {assigned_count} samples | Auto-mapped: {auto_mapped_count} samples"
        if shared_positions > 0:
            status_msg += f" | Shared positions: {shared_positions}"

        self.status_panel.update_status(status_msg)

    def _remove_sample_from_matrix(self, sample: SampleMetadata):
        """Odstraní sample z mapping matrix"""
        keys_to_remove = []
        for key, mapped_sample in self.mapping_matrix.mapping.items():
            if mapped_sample == sample:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.mapping_matrix.mapping[key]
            # Aktualizuj buňku v matici
            if key in self.mapping_matrix.matrix_cells:
                cell = self.mapping_matrix.matrix_cells[key]
                cell.sample = None
                cell._update_style()

    def on_sample_selected(self, sample: SampleMetadata):
        """Obsluha výběru sample ze seznamu - rozšířeno o synchronizaci do matice"""
        # Nastav sample jako aktuální pro přehrávání
        self.audio_player.set_current_sample(sample)

        # Nastav sample v MIDI editoru
        self.sample_editor.set_current_sample(sample)

        # Pokud je sample namapovaný, posun matici na jeho pozici a zvýrazni ho
        if sample.mapped:
            self.mapping_matrix.scroll_to_sample(sample)
            # NOVÝ: Zvýrazni sample v matici (obousměrná synchronizace)
            self.mapping_matrix.highlight_sample_in_matrix(sample)

        # Status s rozšířenými informacemi
        pitch_info = sample.get_pitch_info()
        amplitude_info = sample.get_amplitude_info()

        status_msg = f"Vybrán sample: {sample.filename} | {pitch_info} | {amplitude_info}"
        if sample.mapped:
            status_msg += " | ✓ Namapován"
        elif sample.is_filtered:
            status_msg += " | [FILTROVÁNO] - mimo velocity amplitude rozsah"
        else:
            status_msg += " | Přetáhněte do matice"

        self.status_panel.update_status(status_msg)

    def on_sample_selected_in_matrix(self, sample: SampleMetadata):
        """NOVÝ: Obsluha výběru sample v matici - synchronizace do sample listu"""
        # Nastav sample jako aktuální pro přehrávání
        self.audio_player.set_current_sample(sample)

        # Nastav sample v MIDI editoru
        self.sample_editor.set_current_sample(sample)

        # Zvýrazni sample v seznamu (obousměrná synchronizace)
        self.sample_list.highlight_sample_in_list(sample)

        # Status s rozšířenými informacemi
        pitch_info = sample.get_pitch_info()
        amplitude_info = sample.get_amplitude_info()

        note_name = ""
        velocity_desc = ""

        # Najdi pozici sample v matici pro zobrazení
        for (midi_note, velocity), mapped_sample in self.mapping_matrix.mapping.items():
            if mapped_sample == sample:
                note_name = MidiUtils.midi_to_note_name(midi_note)
                velocity_desc = VelocityUtils.velocity_to_description(velocity)
                break

        position_info = f" na pozici {note_name} V{velocity_desc}" if note_name else ""

        self.status_panel.update_status(
            f"Vybrán sample v matici{position_info}: {sample.filename} | {pitch_info} | {amplitude_info}"
        )

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
        """Obsluha přehrávání sample z mapovací matice"""
        self.audio_player.play_sample(sample)
        pitch_info = sample.get_pitch_info()
        self.status_panel.update_status(f"▶ Přehrává z matice: {sample.filename} ({pitch_info})")

    def on_midi_note_play_requested(self, midi_note: int):
        """Obsluha přehrávání MIDI tónu"""
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

        # Pokud je sample namapovaný, odmapuj ho
        if sample.mapped:
            sample.mapped = False
            self._remove_sample_from_matrix(sample)
            self.mapping_matrix._update_stats()
            self.sample_list.refresh_display()

        self.status_panel.update_status(
            f"MIDI nota změněna: {sample.filename} | {old_note} → {new_note} | Přemapujte sample"
        )

    def on_sample_moved(self, sample: SampleMetadata, old_midi: int, old_velocity: int, new_midi: int,
                        new_velocity: int):
        """Obsluha přesunu sample v mapovací matici"""
        old_note = MidiUtils.midi_to_note_name(old_midi)
        new_note = MidiUtils.midi_to_note_name(new_midi)

        self.sample_list.refresh_display()
        self.update_export_button_state()

        self.status_panel.update_status(
            f"✓ Sample přesunut: {sample.filename} | {old_note}(V{old_velocity}) → {new_note}(V{new_velocity})"
        )

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
        self.status_panel.update_status(f"⚠ Chyba přehrávání: {error}")
        QMessageBox.warning(self, "Chyba přehrávání", error)

    def on_sample_mapped(self, sample: SampleMetadata, midi: int, velocity: int):
        """Obsluha namapování sample přes drag & drop"""
        self.sample_list.refresh_display()
        self.update_export_button_state()

        note_name = MidiUtils.midi_to_note_name(midi)
        velocity_desc = VelocityUtils.velocity_to_description(velocity)

        self.status_panel.update_status(f"✓ Sample namapován: {sample.filename} → {note_name}({velocity_desc})")

    def on_sample_unmapped(self, sample: SampleMetadata, midi: int, velocity: int):
        """Obsluha odmapování sample"""
        self.sample_list.refresh_display()

    def start_batch_analysis(self, folder: Path):
        """Spustí batch analýzu"""
        self.status_panel.show_progress(True)
        self.status_panel.update_progress(0)

        self.analyzer = BatchAnalyzer(folder)
        self.analyzer.progress_updated.connect(self.status_panel.update_progress)
        self.analyzer.analysis_completed.connect(self.on_analysis_completed)
        self.analyzer.start()

    def on_analysis_completed(self, samples: List[SampleMetadata], range_info: dict):
        """Obsluha dokončení analýzy"""
        self.samples = samples
        self.status_panel.show_progress(False)

        if samples:
            pitch_detected = sum(1 for s in samples if s.detected_midi is not None)
            # ZMĚNA: kontrola velocity_amplitude místo peak_amplitude
            velocity_amplitude_detected = sum(1 for s in samples if s.velocity_amplitude is not None)

            self.status_panel.update_status(
                f"✓ Analýza dokončena: {len(samples)} samples | "
                f"Pitch: {pitch_detected}, Velocity amplitude: {velocity_amplitude_detected}"
            )

            # Aktualizuj sample list
            self.sample_list.update_samples(samples)

            # Nastavení amplitude filteru
            self.amplitude_filter.set_amplitude_data(samples, range_info)

            # Auto-mapping několika samples pro demo
            self.auto_map_samples()
        else:
            self.status_panel.update_status("Žádné samples nenalezeny nebo analýza selhala.")

        self.update_export_button_state()

    def auto_map_samples(self):
        """Automatické mapování prvních několika samples"""
        mapped_count = 0

        for sample in self.samples[:5]:
            if (sample.analyzed and not sample.mapped and not sample.is_filtered and
                    sample.detected_midi is not None and sample.velocity_level is not None):

                target_midi = sample.detected_midi
                velocity = min(sample.velocity_level, 7)

                key = (target_midi, velocity)
                if key not in self.mapping_matrix.mapping:
                    self.mapping_matrix.add_sample(sample, target_midi, velocity)
                    mapped_count += 1

        if mapped_count > 0:
            self.status_panel.update_status(f"Auto-mapováno {mapped_count} samples na detekované pozice")

    def update_export_button_state(self):
        """Aktualizuje stav export buttonu"""
        has_output = self.export_manager is not None
        has_mapped = len(self.mapping_matrix.get_mapped_samples()) > 0
        self.control_panel.enable_export(has_output and has_mapped)

    def export_samples(self):
        """Export namapovaných samples"""
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
            QMessageBox.critical(self, "Chyba exportu", f"Chyba při exportu:\n{e}")


def main():
    """Hlavní funkce aplikace"""
    app = QApplication(sys.argv)

    try:
        window = MainWindow()
        window.show()

        # Zobraz tip při spuštění
        from audio_player import AUDIO_AVAILABLE

        audio_status = "✓ Audio k dispozici" if AUDIO_AVAILABLE else "⚠️ Audio není k dispozici"

        QMessageBox.information(window, "Sampler Editor - CREPE Pitch + Velocity Amplitude Detection + Selection Sync",
                                f"Sampler Editor s pokročilou analýzou a obousměrnou synchronizací!\n\n"
                                f"Status: {audio_status}\n\n"
                                "Nové funkce v této verzi:\n"
                                "• CREPE pitch detekce (state-of-the-art)\n"
                                "• Velocity amplitude analýza (RMS prvních 500ms)\n"
                                "• Amplitude filtr s posuvníky\n"
                                "• Dynamické velocity mapování (0-7)\n"
                                "• Vizuální označení filtrovaných samples\n"
                                "• Rozšířené info o každém sample\n"
                                "• OBOUSMĚRNÁ SYNCHRONIZACE VÝBĚRU\n\n"
                                "Workflow:\n"
                                "1. Vyberte vstupní složku → CREPE+velocity amplitude analýza\n"
                                "2. Nastavte amplitude filtr (posuvníky)\n"
                                "3. 'Apply Filter' → označí samples mimo rozsah\n"
                                "4. 'Assign' → přiřadí velocity 0-7 podle RMS amplitude\n"
                                "5. Mapování samples do matice\n"
                                "6. Export s standardní konvencí\n\n"
                                "Synchronizace výběru:\n"
                                "• Klik na sample v seznamu → zvýrazní v matici\n"
                                "• Klik na sample v matici → zvýrazní v seznamu\n"
                                "• Automatický scroll k vybrané pozici\n"
                                "• Vizuální feedback oranžovou barvou\n\n"
                                "Velocity Amplitude Filter:\n"
                                "• Detekovaný rozsah se zobrazí automaticky\n"
                                "• Nastavte min/max pomocí posuvníků nebo čísel\n"
                                "• Samples mimo rozsah = šedá barva\n"
                                "• Velocity se přiřazuje pouze valid samples\n"
                                "• Používá RMS prvních 500ms pro přesnější velocity\n\n"
                                "Klávesy: MEZERNÍK=přehrát | S=porovnat | D=současně | ESC=stop | T=sort")

        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"Chyba aplikace: {e}", exc_info=True)
        QMessageBox.critical(None, "Kritická chyba", f"Aplikace selhala:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()