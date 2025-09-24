"""
drag_drop_helpers.py - Pomocné třídy pro drag & drop operace bez circular imports
"""

from typing import Optional, TYPE_CHECKING
from PySide6.QtWidgets import QMessageBox, QWidget
from PySide6.QtCore import Qt

from models import SampleMetadata
from midi_utils import MidiUtils

# Avoid circular imports
if TYPE_CHECKING:
    from main import MainWindow
    from drag_drop_components import DragDropMappingMatrix


class WidgetFinder:
    """Pomocná třída pro hledání widgetů v aplikaci bez circular imports."""

    @staticmethod
    def find_main_window(widget: QWidget) -> Optional[QWidget]:
        """Najde hlavní okno z daného widgetu pomocí generic přístupu."""
        current = widget
        while current:
            # Look for window with samples attribute (our MainWindow)
            if hasattr(current, 'samples') and hasattr(current, 'mapping_matrix'):
                return current
            current = current.parent()
        return None

    @staticmethod
    def find_sample_by_filename(main_window: QWidget, filename: str) -> Optional[SampleMetadata]:
        """Najde sample podle názvu souboru."""
        if hasattr(main_window, 'samples'):
            for sample in main_window.samples:
                if sample.filename == filename:
                    return sample
        return None

    @staticmethod
    def find_matrix_widget(widget: QWidget) -> Optional[QWidget]:
        """Najde mapping matrix widget z daného widgetu."""
        main_window = WidgetFinder.find_main_window(widget)
        if main_window and hasattr(main_window, 'mapping_matrix'):
            return main_window.mapping_matrix
        return None


class DropHandler:
    """Handler pro drop operace v matrix buňkách."""

    def __init__(self, cell):
        self.cell = cell

    def handle_list_drop(self, event):
        """Obsluha drop ze seznamu samples."""
        filename = event.mimeData().data("application/x-sample-metadata").data().decode()

        # Najdi sample v parent widget
        main_window = WidgetFinder.find_main_window(self.cell)
        if not main_window:
            event.ignore()
            return

        sample = WidgetFinder.find_sample_by_filename(main_window, filename)
        if not sample:
            event.ignore()
            return

        # Kontrola, zda sample není filtrován
        if sample.is_filtered:
            QMessageBox.warning(self.cell, "Filtrovaný sample",
                                f"Sample {sample.filename} je filtrován (mimo amplitude rozsah).\n"
                                f"Nejprve upravte amplitude filter.")
            event.ignore()
            return

        if self.cell.sample:
            # Buňka už je obsazená - zeptej se na přepsání
            reply = QMessageBox.question(self.cell, "Přepsat sample?",
                                         f"Buňka MIDI {self.cell.midi_note}, Velocity {self.cell.velocity} "
                                         f"už obsahuje {self.cell.sample.filename}.\n"
                                         f"Chcete ji přepsat sample {sample.filename}?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return

            # Označ starý sample jako nemapovaný
            self.cell.sample.mapped = False

        # Namapuj nový sample
        self.cell.sample = sample
        sample.mapped = True
        self.cell._update_style()

        # Emit signal
        self.cell.sample_dropped.emit(sample, self.cell.midi_note, self.cell.velocity)
        event.acceptProposedAction()

    def handle_matrix_drop(self, event):
        """Obsluha drop z jiné pozice v matici."""
        data = event.mimeData().data("application/x-matrix-sample").data().decode()
        filename, old_midi_str, old_velocity_str = data.split("|")
        old_midi = int(old_midi_str)
        old_velocity = int(old_velocity_str)

        # Kontrola, že to není drop na stejnou pozici
        if old_midi == self.cell.midi_note and old_velocity == self.cell.velocity:
            event.ignore()
            return

        # Najdi sample v parent widget
        main_window = WidgetFinder.find_main_window(self.cell)
        if not main_window:
            event.ignore()
            return

        sample = WidgetFinder.find_sample_by_filename(main_window, filename)
        if not sample:
            event.ignore()
            return

        # Kontrola obsazené buňky
        if self.cell.sample:
            old_note = MidiUtils.midi_to_note_name(old_midi)
            new_note = MidiUtils.midi_to_note_name(self.cell.midi_note)

            reply = QMessageBox.question(self.cell, "Přepsat sample?",
                                         f"Pozice {new_note} (MIDI {self.cell.midi_note}, V{self.cell.velocity}) "
                                         f"už obsahuje {self.cell.sample.filename}.\n\n"
                                         f"Chcete přesunout {sample.filename} "
                                         f"z {old_note} (MIDI {old_midi}, V{old_velocity}) "
                                         f"a přepsat současný sample?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return

            # Označ přepsaný sample jako nemapovaný
            self.cell.sample.mapped = False

        # Najdi a vyčisti starou pozici
        matrix_widget = WidgetFinder.find_matrix_widget(self.cell)
        if matrix_widget:
            old_key = (old_midi, old_velocity)
            if hasattr(matrix_widget, 'matrix_cells') and old_key in matrix_widget.matrix_cells:
                old_cell = matrix_widget.matrix_cells[old_key]
                old_cell.sample = None
                old_cell._update_style()

                # Odstraň z mapping
                if hasattr(matrix_widget, 'mapping') and old_key in matrix_widget.mapping:
                    del matrix_widget.mapping[old_key]

        # Nastav novou pozici
        self.cell.sample = sample
        self.cell._update_style()

        # Aktualizuj mapping v matrix widget
        if matrix_widget:
            if hasattr(matrix_widget, 'mapping'):
                matrix_widget.mapping[(self.cell.midi_note, self.cell.velocity)] = sample
            if hasattr(matrix_widget, '_update_stats'):
                matrix_widget._update_stats()

        # Emit signál pro přesun
        self.cell.sample_moved.emit(sample, old_midi, old_velocity, self.cell.midi_note, self.cell.velocity)
        event.acceptProposedAction()


class SampleFinder:
    """Utility třída pro hledání samples bez závislosti na konkrétních třídách."""

    @staticmethod
    def find_sample_in_widget_hierarchy(widget: QWidget, filename: str) -> Optional[SampleMetadata]:
        """Najde sample v hierarchii widgetů."""
        current = widget
        while current:
            # Look for any widget with samples attribute
            if hasattr(current, 'samples'):
                for sample in current.samples:
                    if sample.filename == filename:
                        return sample
            current = current.parent()
        return None

    @staticmethod
    def get_application_state(widget: QWidget) -> Optional[dict]:
        """Získá stav aplikace z hierarchie widgetů."""
        main_window = WidgetFinder.find_main_window(widget)
        if main_window:
            return {
                'samples': getattr(main_window, 'samples', []),
                'mapping': getattr(main_window.mapping_matrix, 'mapping', {}) if hasattr(main_window, 'mapping_matrix') else {}
            }
        return None