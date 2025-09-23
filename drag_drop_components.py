"""
drag_drop_components.py - Hlavní drag & drop komponenty (matice a sample list)
"""

from typing import List
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, QLabel,
                               QListWidgetItem, QPushButton, QScrollArea,
                               QGridLayout, QWidget)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from models import SampleMetadata
from midi_utils import MidiUtils, VelocityUtils
from drag_drop_core import DragDropListWidget, DragDropMatrixCell


class DragDropMappingMatrix(QGroupBox):
    """Mapovací matice s podporou drag & drop a celým piano rozsahem"""

    sample_mapped = Signal(object, int, int)  # sample, midi, velocity
    sample_unmapped = Signal(object, int, int)  # sample, midi, velocity
    sample_play_requested = Signal(object)  # sample
    midi_note_play_requested = Signal(int)  # midi_note
    sample_moved = Signal(object, int, int, int, int)  # sample, old_midi, old_velocity, new_midi, new_velocity

    def __init__(self):
        super().__init__("Mapovací matice: Celý piano rozsah A0-C8 (nejvyšší frekvence nahoře)")
        self.mapping = {}  # (midi, velocity) -> SampleMetadata
        self.matrix_cells = {}

        # MIDI rozsah piano
        self.piano_min_midi = MidiUtils.PIANO_MIN_MIDI  # 21 (A0)
        self.piano_max_midi = MidiUtils.PIANO_MAX_MIDI  # 108 (C8)

        self.init_ui()

    def init_ui(self):
        """Inicializace mapovací matice s celým piano rozsahem"""
        layout = QVBoxLayout()

        # Info panel s celkovými statistikami
        self._create_info_panel(layout)

        # Scroll area pro celou matici
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll_area.setMinimumHeight(600)

        # Widget pro matici
        self.matrix_widget = QWidget()
        self._create_full_matrix()

        scroll_area.setWidget(self.matrix_widget)
        layout.addWidget(scroll_area)

        self.setLayout(layout)

    def _create_info_panel(self, layout):
        """Vytvoří info panel s celkovými statistikami"""
        info_layout = QHBoxLayout()

        range_info_label = QLabel(
            f"Celý piano rozsah: A0-C8 (MIDI {self.piano_min_midi}-{self.piano_max_midi}) | Nejvyšší frekvence nahoře")
        range_info_label.setStyleSheet("color: #666; font-size: 12px; font-weight: bold;")
        info_layout.addWidget(range_info_label)

        info_layout.addStretch()

        self.stats_label = QLabel("Namapováno: 0 samples")
        self.stats_label.setStyleSheet("color: #333; font-weight: bold;")
        info_layout.addWidget(self.stats_label)

        layout.addLayout(info_layout)

    def _create_full_matrix(self):
        """Vytvoří matici buněk pro celý piano rozsah"""
        # Vyčisti existující layout
        if self.matrix_widget.layout():
            while self.matrix_widget.layout().count():
                child = self.matrix_widget.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

        matrix_layout = QGridLayout()
        matrix_layout.setSpacing(2)  # Menší spacing pro kompaktnější zobrazení

        # Header řádek
        matrix_layout.addWidget(self._create_header_label("MIDI"), 0, 0)
        matrix_layout.addWidget(self._create_header_label("Nota"), 0, 1)
        for vel in range(8):
            vel_label = self._create_header_label(f"V{vel}")
            matrix_layout.addWidget(vel_label, 0, vel + 2)

        # Vytvoř buňky pro celý piano rozsah - od nejvyšší noty (C8) k nejnižší (A0)
        self.matrix_cells.clear()

        # Seřazení od nejvyšší po nejnižší MIDI notu
        midi_notes = list(range(self.piano_min_midi, self.piano_max_midi + 1))
        midi_notes.reverse()  # C8 (108) na vrcholu, A0 (21) na spodku

        for i, midi_note in enumerate(midi_notes):
            row = i + 1

            # MIDI číslo - klikací pro přehrávání tónu
            midi_label = self._create_clickable_midi_label(midi_note)
            matrix_layout.addWidget(midi_label, row, 0)

            # Nota jméno
            note_name = MidiUtils.midi_to_note_name(midi_note)
            note_label = QLabel(note_name)
            note_label.setAlignment(Qt.AlignCenter)
            note_label.setStyleSheet(
                "background-color: #f5f5f5; padding: 3px; border-radius: 3px; font-weight: bold; font-size: 10px;")
            matrix_layout.addWidget(note_label, row, 1)

            # Velocity buňky
            for velocity in range(8):
                cell = DragDropMatrixCell(midi_note, velocity)
                cell.sample_dropped.connect(self._on_sample_dropped)
                cell.sample_play_requested.connect(self.sample_play_requested.emit)
                cell.sample_moved.connect(self._on_sample_moved)

                # Pokud už je namapovaný sample, nastav ho
                key = (midi_note, velocity)
                if key in self.mapping:
                    cell.sample = self.mapping[key]
                    cell._update_style()

                matrix_layout.addWidget(cell, row, velocity + 2)
                self.matrix_cells[(midi_note, velocity)] = cell

        self.matrix_widget.setLayout(matrix_layout)

    def _create_header_label(self, text: str) -> QLabel:
        """Vytvoří header label pro matici"""
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                font-weight: bold; 
                background-color: #e0e0e0; 
                padding: 5px; 
                border-radius: 3px;
                color: #333;
                border: 1px solid #ccc;
                font-size: 11px;
            }
        """)
        return label

    def _create_clickable_midi_label(self, midi_note: int) -> QPushButton:
        """Vytvoří klikací MIDI label pro přehrávání tónu"""
        label = QPushButton(str(midi_note))
        label.setFixedSize(40, 30)
        label.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: 1px solid #2980b9;
                border-radius: 3px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        label.setToolTip(f"Klik = přehrát MIDI tón {midi_note} ({MidiUtils.midi_to_note_name(midi_note)})")
        label.clicked.connect(lambda: self.midi_note_play_requested.emit(midi_note))
        return label

    def _on_sample_dropped(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """Obsluha drop sample na buňku"""
        key = (midi_note, velocity)
        old_sample = self.mapping.get(key)

        if old_sample and old_sample != sample:
            old_sample.mapped = False
            self.sample_unmapped.emit(old_sample, midi_note, velocity)

        self.mapping[key] = sample
        self._update_stats()
        self.sample_mapped.emit(sample, midi_note, velocity)

    def _on_sample_moved(self, sample: SampleMetadata, old_midi: int, old_velocity: int, new_midi: int,
                         new_velocity: int):
        """Obsluha přesunu sample v matici"""
        # Signál je už zpracovaný v buňce, jen předáváme dál a aktualizujeme stats
        self._update_stats()
        self.sample_moved.emit(sample, old_midi, old_velocity, new_midi, new_velocity)

    def add_sample(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """Programově přidá sample (pro auto-mapping)"""
        key = (midi_note, velocity)
        self.mapping[key] = sample
        sample.mapped = True

        # Aktualizuj buňku pokud je zobrazená
        if key in self.matrix_cells:
            cell = self.matrix_cells[key]
            cell.sample = sample
            cell._update_style()

        self._update_stats()
        self.sample_mapped.emit(sample, midi_note, velocity)

    def get_mapped_samples(self) -> List[SampleMetadata]:
        """Vrátí všechny namapované samples"""
        return list(self.mapping.values())

    def _update_stats(self):
        """Aktualizuje statistiky"""
        count = len(self.mapping)
        self.stats_label.setText(f"Namapováno: {count} samples")

    def scroll_to_sample(self, sample: SampleMetadata):
        """Posune zobrazení na pozici obsahující daný sample"""
        for (midi_note, velocity), mapped_sample in self.mapping.items():
            if mapped_sample == sample:
                # Najdi widget buňky a poskoč na něj
                if (midi_note, velocity) in self.matrix_cells:
                    cell = self.matrix_cells[(midi_note, velocity)]
                    # Spočítej řádek v matici (nejvyšší MIDI má řádek 1)
                    row_index = self.piano_max_midi - midi_note + 1

                    # Najdi scroll area parent
                    scroll_area = None
                    parent = cell.parent()
                    while parent:
                        if isinstance(parent, QScrollArea):
                            scroll_area = parent
                            break
                        parent = parent.parent()

                    if scroll_area:
                        # Aproximace pozice pro scroll
                        cell_height = 37  # Výška buňky + spacing
                        target_y = row_index * cell_height
                        scroll_area.verticalScrollBar().setValue(target_y - 200)  # Offset pro lepší viditelnost
                break

    def get_displayed_range(self):
        """Vrátí celý piano rozsah (pro kompatibilitu)"""
        return (self.piano_min_midi, self.piano_max_midi)


class DragDropSampleList(QGroupBox):
    """Seznam samples s podporou drag operací a rozšířenými informacemi"""

    sample_selected = Signal(object)
    play_requested = Signal(object)
    compare_requested = Signal(object)
    simultaneous_requested = Signal(object)

    def __init__(self):
        super().__init__("Analyzované samples - MEZERNÍK = přehrát | S = porovnat | D = současně")
        self.samples = []
        self.init_ui()

    def init_ui(self):
        """Inicializace seznamu s drag podporou"""
        layout = QVBoxLayout()

        # Info panel
        self.info_label = QLabel("Žádné samples načteny")
        self.info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.info_label)

        # Instrukce s přehráváním
        instructions = QLabel(
            "Tip: Přetáhněte sample do matice | "
            "MEZERNÍK = přehrát | S = porovnat (tón→sample) | D = současně (tón+sample) | "
            "Šedá barva = filtrováno"
        )
        instructions.setStyleSheet(
            "color: #0066cc; font-size: 12px; background-color: #f0f8ff; "
            "padding: 8px; border-radius: 4px; border: 1px solid #cce7ff;"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Seznam s drag podporou a klávesovými zkratkami
        self.sample_list = DragDropListWidget()
        self.sample_list.itemClicked.connect(self._on_item_clicked)
        self.sample_list.play_requested.connect(self.play_requested.emit)
        self.sample_list.compare_requested.connect(self.compare_requested.emit)
        self.sample_list.simultaneous_requested.connect(self.simultaneous_requested.emit)
        layout.addWidget(self.sample_list)

        self.setLayout(layout)

    def update_samples(self, samples: List[SampleMetadata]):
        """Aktualizuje seznam samples s rozšířenými informacemi"""
        self.samples = samples
        self.sample_list.clear()

        if not samples:
            self.info_label.setText("Žádné samples načteny")
            return

        # Statistiky
        total_count = len(samples)
        pitch_detected = sum(1 for s in samples if s.detected_midi is not None)
        amplitude_detected = sum(1 for s in samples if s.peak_amplitude is not None)
        filtered_count = sum(1 for s in samples if s.is_filtered)
        mapped_count = sum(1 for s in samples if s.mapped)

        self.info_label.setText(
            f"Načteno {total_count} samples | Pitch: {pitch_detected} | Amplitude: {amplitude_detected} | "
            f"Filtrováno: {filtered_count} | Namapováno: {mapped_count}"
        )

        for sample in samples:
            # Vytvoř rozšířený text pro item
            item_text = self._create_sample_item_text(sample)

            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, sample)

            # Barva podle stavu
            self._set_item_colors_and_tooltip(item, sample)

            self.sample_list.addItem(item)

    def _create_sample_item_text(self, sample: SampleMetadata) -> str:
        """Vytvoří text pro sample item"""
        item_text = f"{sample.filename}\n"

        # Pitch info
        if sample.detected_midi:
            note_name = MidiUtils.midi_to_note_name(sample.detected_midi)
            pitch_line = f"  🎵 {note_name} (MIDI {sample.detected_midi}"
            if sample.pitch_confidence:
                pitch_line += f", conf: {sample.pitch_confidence:.2f}"
            if sample.pitch_method:
                pitch_line += f", {sample.pitch_method}"
            pitch_line += ")"
            item_text += pitch_line + "\n"
        else:
            item_text += "  🎵 No pitch detected\n"

        # Amplitude info
        if sample.peak_amplitude is not None:
            amp_line = f"  📊 Peak: {sample.peak_amplitude:.6f}"
            if sample.peak_amplitude_db is not None:
                amp_line += f" ({sample.peak_amplitude_db:.1f} dB)"
            if sample.velocity_level is not None:
                velocity_desc = VelocityUtils.velocity_to_description(sample.velocity_level)
                amp_line += f" → {velocity_desc} (V{sample.velocity_level})"
            item_text += amp_line + "\n"
        else:
            item_text += "  📊 No amplitude data\n"

        # Status info
        if sample.is_filtered:
            item_text += "  ⚠️ FILTERED - outside amplitude range"
        elif sample.mapped:
            item_text += "  ✅ MAPPED to matrix"
        else:
            item_text += "  📌 Ready for mapping"

        return item_text

    def _set_item_colors_and_tooltip(self, item: QListWidgetItem, sample: SampleMetadata):
        """Nastaví barvy a tooltip pro item"""
        # Barva podle stavu
        if sample.is_filtered:
            # Šedá barva pro filtrované samples
            item.setBackground(QColor("#e0e0e0"))
            item.setForeground(QColor("#666666"))
            tooltip_text = (f"FILTROVANÝ SAMPLE - mimo amplitude rozsah\n"
                            f"Soubor: {sample.filename}\n"
                            f"Použijte Amplitude Filter pro změnu rozsahu")
        elif sample.mapped:
            # Zelená pro namapované
            item.setBackground(QColor("#e8f5e8"))
            tooltip_text = (f"Sample je namapován v matici\n"
                            f"MEZERNÍK = přehrát | S = porovnat | D = současně")
        else:
            # Bílá pro připravené k mapování
            item.setBackground(QColor("#ffffff"))
            tooltip_text = (f"Připraveno k mapování\n"
                            f"Přetáhněte do mapovací matice\n"
                            f"MEZERNÍK = přehrát | S = porovnat | D = současně")

        # Rozšířený tooltip s detailními informacemi
        tooltip_text += self._create_detailed_tooltip(sample)
        item.setToolTip(tooltip_text)

    def _create_detailed_tooltip(self, sample: SampleMetadata) -> str:
        """Vytvoří detailní tooltip pro sample"""
        tooltip_addition = ""

        if sample.detected_midi:
            note_name = MidiUtils.midi_to_note_name(sample.detected_midi)
            tooltip_addition += f"\n\nPitch: {note_name} (MIDI {sample.detected_midi})"
            if sample.pitch_confidence:
                tooltip_addition += f"\nConfidence: {sample.pitch_confidence:.2f}"
            if sample.pitch_method:
                tooltip_addition += f"\nMethod: {sample.pitch_method}"

        if sample.peak_amplitude is not None:
            tooltip_addition += f"\n\nPeak amplitude: {sample.peak_amplitude:.6f}"
            if sample.peak_amplitude_db is not None:
                tooltip_addition += f" ({sample.peak_amplitude_db:.1f} dB)"
            if sample.velocity_level is not None:
                velocity_desc = VelocityUtils.velocity_to_description(sample.velocity_level)
                tooltip_addition += f"\nVelocity: {velocity_desc} (Level {sample.velocity_level})"

        return tooltip_addition

    def _on_item_clicked(self, item):
        """Obsluha kliknutí na item"""
        sample = item.data(Qt.UserRole)
        self.sample_selected.emit(sample)

    def refresh_display(self):
        """Obnoví zobrazení (zachová aktuální seznam)"""
        self.update_samples(self.samples)