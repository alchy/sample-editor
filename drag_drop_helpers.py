"""
drag_drop_helpers.py - Pomocné třídy pro drag & drop operace
"""

from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Qt

from models import SampleMetadata
from midi_utils import MidiUtils


class DropHandler:
    """Handler pro drop operace v matrix buňkách"""

    def __init__(self, cell):
        self.cell = cell

    def handle_list_drop(self, event):
        """Obsluha drop ze seznamu samples"""
        filename = event.mimeData().data("application/x-sample-metadata").data().decode()

        # Import zde kvůli circular imports
        from drag_drop_core import WidgetFinder

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
                                f"Nejprve upravte amplitude filter nebo přiřaďte velocity levels.")
            event.ignore()
            return

        if self.cell.sample:
            # Buňka už je obsazená - zeptej se na přepsání
            reply = QMessageBox.question(self.cell, "Přepsat sample?",
                                         f"Buňka MIDI {self.cell.midi_note}, Velocity {self.cell.velocity} "
                                         f"už obsahuje {self.cell.sample.filename}.\n"
                                         f"Chcete ji přepsat sample {sample.filename}?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
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
        """Obsluha drop z jiné pozice v matici"""
        data = event.mimeData().data("application/x-matrix-sample").data().decode()
        filename, old_midi_str, old_velocity_str = data.split("|")
        old_midi = int(old_midi_str)
        old_velocity = int(old_velocity_str)

        # Kontrola, že to není drop na stejnou pozici
        if old_midi == self.cell.midi_note and old_velocity == self.cell.velocity:
            event.ignore()
            return

        # Import zde kvůli circular imports
        from drag_drop_core import WidgetFinder

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
                                         QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                event.ignore()
                return

            # Označ přepsaný sample jako nemapovaný
            self.cell.sample.mapped = False

        # Najdi a vyčisti starou pozici
        matrix_widget = WidgetFinder.find_matrix_widget(self.cell)
        if matrix_widget:
            old_key = (old_midi, old_velocity)
            if old_key in matrix_widget.matrix_cells:
                old_cell = matrix_widget.matrix_cells[old_key]
                old_cell.sample = None
                old_cell._update_style()

                # Odstraň z mapping
                if old_key in matrix_widget.mapping:
                    del matrix_widget.mapping[old_key]

        # Nastav novou pozici
        self.cell.sample = sample
        self.cell._update_style()

        # Aktualizuj mapping v matrix widget
        if matrix_widget:
            matrix_widget.mapping[(self.cell.midi_note, self.cell.velocity)] = sample
            matrix_widget._update_stats()

        # Emit signál pro přesun
        self.cell.sample_moved.emit(sample, old_midi, old_velocity, self.cell.midi_note, self.cell.velocity)
        event.acceptProposedAction()