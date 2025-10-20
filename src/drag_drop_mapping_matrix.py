"""
drag_drop_mapping_matrix.py - Mapovací matice s center-based auto-assign algoritmem
"""

from typing import Dict, List, Tuple, Optional
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QScrollArea, QGridLayout, QWidget, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from config import GUI
from .models import SampleMetadata
from .midi_utils import MidiUtils
from .drag_drop_matrix_core import DragDropMatrixCell  # OPRAVENÝ IMPORT
import logging

logger = logging.getLogger(__name__)


class DragDropMappingMatrix(QGroupBox):
    """Mapovací matice - zachovává všechnu funkcionalitu včetně center-based auto-assign."""

    sample_mapped = Signal(object, int, int)  # sample, midi, velocity
    sample_unmapped = Signal(object, int, int)  # sample, midi, velocity
    sample_play_requested = Signal(object)  # sample
    midi_note_play_requested = Signal(int)  # midi_note
    sample_moved = Signal(object, int, int, int, int)  # sample, old_midi, old_velocity, new_midi, new_velocity
    sample_selected_in_matrix = Signal(object)  # sample vybraný v matici

    def __init__(self, velocity_layers: int = 4):
        super().__init__(GUI.Texts.MATRIX_TITLE)
        self.mapping: Dict[Tuple[int, int], SampleMetadata] = {}
        self.matrix_cells: Dict[Tuple[int, int], DragDropMatrixCell] = {}

        # MIDI rozsah piano
        self.piano_min_midi = MidiUtils.PIANO_MIN_MIDI  # 21 (A0)
        self.piano_max_midi = MidiUtils.PIANO_MAX_MIDI  # 108 (C8)

        # Velocity layers (dynamické podle session)
        self.velocity_layers = velocity_layers

        self.init_ui()

    def init_ui(self):
        """Inicializace mapovací matice s celým piano rozsahem."""
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
        """Vytvoří info panel s celkovými statistikami."""
        info_layout = QHBoxLayout()

        # Rozsah piano
        range_info_text = GUI.Texts.MATRIX_RANGE_INFO_TEMPLATE.format(
            min_midi=self.piano_min_midi,
            max_midi=self.piano_max_midi
        )
        range_info_label = QLabel(range_info_text)
        range_info_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        info_layout.addWidget(range_info_label)

        info_layout.addStretch()

        # Statistiky
        stats_text = GUI.Texts.MATRIX_MAPPED_TEMPLATE.format(count=0)
        self.stats_label = QLabel(stats_text)
        self.stats_label.setStyleSheet("color: #2c3e50; font-weight: bold; font-size: 11px;")
        info_layout.addWidget(self.stats_label)

        layout.addLayout(info_layout)

    def _create_full_matrix(self):
        """Vytvoří matici buněk pro celý piano rozsah."""
        # Vyčisti existující layout
        if self.matrix_widget.layout():
            while self.matrix_widget.layout().count():
                child = self.matrix_widget.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

        matrix_layout = QGridLayout()
        matrix_layout.setSpacing(2)

        # Header řádek
        matrix_layout.addWidget(self._create_header_label("MIDI"), 0, 0)
        matrix_layout.addWidget(self._create_header_label("Nota"), 0, 1)
        matrix_layout.addWidget(self._create_header_label("Play"), 0, 2)
        matrix_layout.addWidget(self._create_header_label("Reset"), 0, 3)
        matrix_layout.addWidget(self._create_header_label("Assign"), 0, 4)
        for vel in range(self.velocity_layers):
            vel_label = self._create_header_label(f"V{vel}")
            matrix_layout.addWidget(vel_label, 0, vel + 5)

        # Vytvoř buňky pro celý piano rozsah - od nejvyšší noty (C8) k nejnižší (A0)
        self.matrix_cells.clear()

        # Seřazení od nejvyšší po nejnižší MIDI notu
        midi_notes = list(range(self.piano_min_midi, self.piano_max_midi + 1))
        midi_notes.reverse()  # C8 (108) na vrcholu, A0 (21) na spodku

        for i, midi_note in enumerate(midi_notes):
            row = i + 1

            # MIDI číslo
            midi_label = QLabel(str(midi_note))
            midi_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            midi_label.setStyleSheet("background-color: #f0f0f0; border: none; font-size: 10px; padding: 2px;")
            matrix_layout.addWidget(midi_label, row, 0)

            # Nota jméno
            note_name = MidiUtils.midi_to_note_name(midi_note)
            note_label = QLabel(note_name)
            note_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            note_label.setStyleSheet(
                "background-color: #f5f5f5; padding: 3px; border-radius: 3px; font-weight: bold; font-size: 10px;")
            matrix_layout.addWidget(note_label, row, 1)

            # Play tlačítko pro MIDI tón
            play_button = self._create_play_midi_button(midi_note)
            matrix_layout.addWidget(play_button, row, 2)

            # Reset tlačítko pro notu
            reset_button = self._create_reset_note_button(midi_note)
            matrix_layout.addWidget(reset_button, row, 3)

            # Assign tlačítko pro notu
            assign_button = self._create_assign_note_button(midi_note)
            matrix_layout.addWidget(assign_button, row, 4)

            # Velocity buňky (dynamický počet podle velocity_layers)
            for velocity in range(self.velocity_layers):
                cell = DragDropMatrixCell(midi_note, velocity)
                # Připoj všechny signály
                cell.sample_dropped.connect(self._on_sample_dropped)
                cell.sample_removed.connect(self._on_sample_removed)
                cell.sample_clicked.connect(self.sample_selected_in_matrix.emit)
                cell.sample_play_requested.connect(self.sample_play_requested.emit)
                cell.sample_moved.connect(self.sample_moved.emit)
                matrix_layout.addWidget(cell, row, velocity + 5)

                key = (midi_note, velocity)
                self.matrix_cells[key] = cell

        self.matrix_widget.setLayout(matrix_layout)

    def _create_header_label(self, text: str) -> QLabel:
        """Vytvoří header label."""
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-weight: bold; background-color: #e0e0e0; padding: 5px;")
        return label

    def _create_play_midi_button(self, midi_note: int) -> QPushButton:
        """Vytvoří play tlačítko pro MIDI tón."""
        button = QPushButton("♪")
        button.setMaximumWidth(20)
        button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50; 
                    color: white; 
                    font-weight: bold;
                    border-radius: 3px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
        button.clicked.connect(lambda: self._play_midi_note(midi_note))
        button.setToolTip(f"Přehrát MIDI tón {midi_note}")
        return button

    def _create_reset_note_button(self, midi_note: int) -> QPushButton:
        """Vytvoří reset tlačítko pro notu."""
        button = QPushButton("⌫")
        button.setMaximumWidth(20)
        button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336; 
                    color: white; 
                    font-weight: bold;
                    border-radius: 3px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
        button.clicked.connect(lambda: self._reset_note(midi_note))
        button.setToolTip(f"Odstranit všechny samples pro MIDI {midi_note}")
        return button

    def _create_assign_note_button(self, midi_note: int) -> QPushButton:
        """Vytvoří assign tlačítko pro notu."""
        button = QPushButton("⚡")
        button.setMaximumWidth(20)
        button.setStyleSheet("""
                QPushButton {
                    background-color: #ff9800; 
                    color: white; 
                    font-weight: bold;
                    border-radius: 3px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #f57c00;
                }
            """)
        button.clicked.connect(lambda: self._auto_assign_note(midi_note))
        button.setToolTip(f"Auto-přiřadit samples pro MIDI {midi_note} podle RMS")
        return button

    def _play_midi_note(self, midi_note: int):
        """Přehraje MIDI notu pomocí správného signálu."""
        logger.debug(f"Playing MIDI note {midi_note}")
        self.midi_note_play_requested.emit(midi_note)

    def _reset_note(self, midi_note: int):
        """Odstraní všechny samples pro danou notu."""
        removed_count = 0
        for velocity in range(self.velocity_layers):
            key = (midi_note, velocity)
            if key in self.matrix_cells and self.matrix_cells[key].sample:
                self.remove_sample(midi_note, velocity)
                removed_count += 1

        if removed_count > 0:
            note_name = MidiUtils.midi_to_note_name(midi_note)
            logger.info(f"Reset note {note_name} (MIDI {midi_note}): removed {removed_count} samples")

    def _auto_assign_note(self, midi_note: int):
        """Center-based auto-assign algoritmus."""
        matching_samples = self._find_samples_for_midi_note(midi_note)

        if not matching_samples:
            note_name = MidiUtils.midi_to_note_name(midi_note)
            logger.info(f"No samples found for auto-assign of {note_name} (MIDI {midi_note})")
            return

        available_samples = [s for s in matching_samples if not s.mapped and s.velocity_amplitude is not None]

        if not available_samples:
            logger.info(f"No unmapped samples with RMS data available for {MidiUtils.midi_to_note_name(midi_note)}")
            return

        rms_values = [s.velocity_amplitude for s in available_samples]
        min_rms = min(rms_values)
        max_rms = max(rms_values)

        assigned_count = 0

        if min_rms == max_rms:
            self._assign_sample_to_velocity(available_samples[0], midi_note, 0)
            assigned_count = 1
        else:
            range_size = max_rms - min_rms

            for velocity in range(self.velocity_layers):
                part_start = min_rms + (velocity / float(self.velocity_layers)) * range_size
                part_end = min_rms + ((velocity + 1) / float(self.velocity_layers)) * range_size
                part_center = (part_start + part_end) / 2.0

                best_sample = None
                best_distance = float('inf')

                for sample in available_samples:
                    distance = abs(sample.velocity_amplitude - part_center)
                    if distance < best_distance:
                        best_sample = sample
                        best_distance = distance

                if best_sample:
                    self._assign_sample_to_velocity(best_sample, midi_note, velocity)
                    available_samples.remove(best_sample)
                    assigned_count += 1

        note_name = MidiUtils.midi_to_note_name(midi_note)
        logger.info(f"Auto-assigned {assigned_count} samples for {note_name} (MIDI {midi_note}) "
                    f"using center-based algorithm (RMS range: {min_rms:.6f} - {max_rms:.6f})")

    def _find_samples_for_midi_note(self, midi_note: int) -> List[SampleMetadata]:
        """Najde všechny samples s danou MIDI notou (kromě disabled a filtered)."""
        main_window = self._find_main_window()
        if not main_window or not hasattr(main_window, 'samples'):
            return []

        matching_samples = []
        for sample in main_window.samples:
            # Kontrola disabled flagu (pokud existuje)
            is_disabled = getattr(sample, 'disabled', False)

            if (sample.detected_midi == midi_note and
                    not sample.is_filtered and
                    not is_disabled and  # OPRAVA: Přidána kontrola disabled
                    sample.velocity_amplitude is not None):
                matching_samples.append(sample)

        return matching_samples

    def _find_main_window(self):
        """Najde main window v hierarchii."""
        current = self.parent()
        while current:
            if hasattr(current, 'samples'):
                return current
            current = current.parent()
        return None

    def _assign_sample_to_velocity(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """Přiřadí sample na konkrétní MIDI pozici."""
        key = (midi_note, velocity)
        if key in self.mapping:
            old_sample = self.mapping[key]
            old_sample.mapped = False
        self.add_sample(sample, midi_note, velocity)

    def auto_assign_all_notes(self) -> Dict[str, int]:
        """
        Provede auto-assign pro všechny MIDI noty (celý piano rozsah).

        Returns:
            Dictionary se statistikami:
            - total_notes: Celkový počet zpracovaných not
            - assigned_notes: Počet not s přiřazenými samples
            - total_samples: Celkový počet přiřazených samples
        """
        stats = {
            'total_notes': 0,
            'assigned_notes': 0,
            'total_samples': 0
        }

        logger.info(f"Starting auto-assign for all notes (MIDI {self.piano_min_midi}-{self.piano_max_midi})...")

        # Projdi všechny MIDI noty v piano rozsahu
        for midi_note in range(self.piano_min_midi, self.piano_max_midi + 1):
            stats['total_notes'] += 1

            # Spočítej kolik samples bylo před assign
            before_count = sum(1 for key in self.mapping.keys() if key[0] == midi_note)

            # Proveď auto-assign pro tuto notu
            self._auto_assign_note(midi_note)

            # Spočítej kolik samples je po assign
            after_count = sum(1 for key in self.mapping.keys() if key[0] == midi_note)

            # Pokud se něco přiřadilo, započítej
            if after_count > before_count:
                stats['assigned_notes'] += 1
                stats['total_samples'] += (after_count - before_count)

        logger.info(f"Auto-assign all completed: {stats['assigned_notes']}/{stats['total_notes']} notes assigned, "
                   f"{stats['total_samples']} total samples")

        return stats

    def clear_matrix(self):
        """Vyčistí celou mapovací matici."""
        for key in list(self.mapping.keys()):
            midi_note, velocity = key
            self.remove_sample(midi_note, velocity)

    def clear_matrix_bulk(self):
        """
        Vyčistí celou mapovací matici v bulk režimu - bez GUI updates během procesu.
        GUI se updatuje jen jednou na konci. Vhodné pro threading.
        """
        # Unmap all samples
        for sample in self.mapping.values():
            sample.mapped = False

        # Clear all cells (without individual GUI updates)
        for cell in self.matrix_cells.values():
            if cell.sample:
                cell.sample = None

        # Clear mapping dictionary
        self.mapping.clear()

        # Now update GUI once at the end
        for cell in self.matrix_cells.values():
            cell._update_style()

        self._update_stats()

    def add_sample(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """Přidá sample do matice."""
        key = (midi_note, velocity)
        if key in self.matrix_cells:
            cell = self.matrix_cells[key]
            if cell.sample:
                cell.sample.mapped = False

            cell.sample = sample
            sample.mapped = True
            cell._update_style()
            self.mapping[key] = sample
            self._update_stats()

            self.sample_mapped.emit(sample, midi_note, velocity)

    def add_sample_silent(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """
        Přidá sample do matice bez GUI updates a signálů.
        Použití: bulk operace kde GUI update proběhne jednou na konci.
        """
        key = (midi_note, velocity)
        if key in self.matrix_cells:
            cell = self.matrix_cells[key]
            if cell.sample:
                cell.sample.mapped = False

            cell.sample = sample
            sample.mapped = True
            self.mapping[key] = sample

    def refresh_all_cells(self):
        """
        Aktualizuje GUI všech buněk najednou.
        Použití: po bulk operacích (add_sample_silent).
        """
        for cell in self.matrix_cells.values():
            cell._update_style()
        self._update_stats()

    def remove_sample(self, midi_note: int, velocity: int):
        """Odebere sample z matice."""
        key = (midi_note, velocity)
        if key in self.matrix_cells:
            cell = self.matrix_cells[key]
            if cell.sample:
                sample = cell.sample
                sample.mapped = False
                cell.sample = None
                cell._update_style()
                if key in self.mapping:
                    del self.mapping[key]
                self._update_stats()
                self.sample_unmapped.emit(sample, midi_note, velocity)

    def _on_sample_dropped(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """Handler pro drop sample."""
        key = (midi_note, velocity)
        self.mapping[key] = sample
        self._update_stats()
        self.sample_mapped.emit(sample, midi_note, velocity)

    def _on_sample_removed(self, sample: SampleMetadata, midi_note: int, velocity: int):
        """Handler pro odebrání sample."""
        key = (midi_note, velocity)
        if key in self.mapping:
            del self.mapping[key]
            self._update_stats()
        self.sample_unmapped.emit(sample, midi_note, velocity)

    def _update_stats(self):
        """Aktualizuje statistiky."""
        stats_text = GUI.Texts.MATRIX_MAPPED_TEMPLATE.format(count=len(self.mapping))
        self.stats_label.setText(stats_text)

    def get_mapped_samples(self) -> Dict[Tuple[int, int], SampleMetadata]:
        """Vrátí mapování."""
        return self.mapping

    def highlight_sample_in_matrix(self, sample: SampleMetadata):
        """Zvýrazní sample v matici."""
        for cell in self.matrix_cells.values():
            cell.highlight_if_matches(sample)

    def find_cell_by_sample(self, sample: SampleMetadata) -> Optional[DragDropMatrixCell]:
        """Najde buňku podle sample."""
        for cell in self.matrix_cells.values():
            if cell.sample == sample:
                return cell
        return None