"""
amplitude_filter_widget.py - GUI komponenta pro filtraci amplitude
"""

from typing import Optional, List
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QSlider, QDoubleSpinBox, QFrame, QProgressBar)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from models import SampleMetadata, AmplitudeFilterSettings


class AmplitudeFilterWidget(QGroupBox):
    """Widget pro nastavení amplitude filtru a velocity mappingu"""

    filter_applied = Signal(object)  # AmplitudeFilterSettings
    velocity_assigned = Signal(object)  # AmplitudeFilterSettings

    def __init__(self):
        super().__init__("Amplitude Filter & Velocity Assignment")
        self.filter_settings = AmplitudeFilterSettings()
        self.samples = []
        self.init_ui()
        self.update_display()

    def init_ui(self):
        """Inicializuje UI komponenty"""
        layout = QVBoxLayout()

        # Hlavní horizontální rozdělení
        main_horizontal_layout = QHBoxLayout()

        # Levá polovina - slidery
        self._create_slider_section(main_horizontal_layout)

        # Pravá polovina - textové informace
        self._create_info_section(main_horizontal_layout)

        layout.addLayout(main_horizontal_layout)

        # Akční tlačítka zůstávají dole
        self._create_action_buttons(layout)

        self.setLayout(layout)
        self.setMaximumHeight(200)

    def _create_slider_section(self, main_layout):
        """Vytvoří levou sekci s posuvníky"""
        slider_frame = QFrame()
        slider_frame.setStyleSheet(
            "QFrame { background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 3px; }")
        slider_layout = QVBoxLayout()

        # Nadpis pro slider sekci
        slider_title = QLabel("Amplitude Range")
        slider_title.setStyleSheet("font-weight: bold; color: #333; font-size: 12px; text-align: center;")
        slider_title.setAlignment(Qt.AlignCenter)
        slider_layout.addWidget(slider_title)

        # Min hodnota
        min_layout = QHBoxLayout()
        min_label = QLabel("Min:")
        min_label.setMinimumWidth(30)
        min_layout.addWidget(min_label)

        self.min_slider = QSlider(Qt.Horizontal)
        self.min_slider.setMinimum(0)
        self.min_slider.setMaximum(10000)  # Budeme škálovat
        self.min_slider.valueChanged.connect(self._on_min_slider_changed)
        min_layout.addWidget(self.min_slider)

        self.min_spinbox = QDoubleSpinBox()
        self.min_spinbox.setDecimals(6)
        self.min_spinbox.setMinimum(0.0)
        self.min_spinbox.setMaximum(10.0)
        self.min_spinbox.setSingleStep(0.000001)
        self.min_spinbox.valueChanged.connect(self._on_min_spinbox_changed)
        self.min_spinbox.setMaximumWidth(100)
        min_layout.addWidget(self.min_spinbox)

        slider_layout.addLayout(min_layout)

        # Max hodnota
        max_layout = QHBoxLayout()
        max_label = QLabel("Max:")
        max_label.setMinimumWidth(30)
        max_layout.addWidget(max_label)

        self.max_slider = QSlider(Qt.Horizontal)
        self.max_slider.setMinimum(0)
        self.max_slider.setMaximum(10000)
        self.max_slider.valueChanged.connect(self._on_max_slider_changed)
        max_layout.addWidget(self.max_slider)

        self.max_spinbox = QDoubleSpinBox()
        self.max_spinbox.setDecimals(6)
        self.max_spinbox.setMinimum(0.0)
        self.max_spinbox.setMaximum(10.0)
        self.max_spinbox.setSingleStep(0.000001)
        self.max_spinbox.valueChanged.connect(self._on_max_spinbox_changed)
        self.max_spinbox.setMaximumWidth(100)
        max_layout.addWidget(self.max_spinbox)

        slider_layout.addLayout(max_layout)

        slider_frame.setLayout(slider_layout)
        main_layout.addWidget(slider_frame)

    def _create_info_section(self, main_layout):
        """Vytvoří pravou sekci s textovými informacemi"""
        info_frame = QFrame()
        info_frame.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 3px; }")
        info_layout = QVBoxLayout()

        # Nadpis pro info sekci
        info_title = QLabel("Detection Info")
        info_title.setStyleSheet("font-weight: bold; color: #333; font-size: 12px; text-align: center;")
        info_title.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(info_title)

        # Detekovaný rozsah
        self.range_label = QLabel("Detected range: No data")
        self.range_label.setStyleSheet("font-weight: bold; color: #333; font-size: 11px;")
        info_layout.addWidget(self.range_label)

        # Statistiky
        self.stats_label = QLabel("Statistics: No data")
        self.stats_label.setStyleSheet("color: #666; font-size: 10px;")
        info_layout.addWidget(self.stats_label)

        # Samples info
        self.samples_label = QLabel("Valid samples: 0/0")
        self.samples_label.setStyleSheet("color: #28a745; font-weight: bold; font-size: 11px;")
        info_layout.addWidget(self.samples_label)

        info_frame.setLayout(info_layout)
        main_layout.addWidget(info_frame)

    def _create_action_buttons(self, layout):
        """Vytvoří akční tlačítka"""
        button_layout = QHBoxLayout()

        # Reset tlačítko
        self.reset_button = QPushButton("Reset to Full Range")
        self.reset_button.clicked.connect(self._reset_to_full_range)
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d; 
                color: white; 
                font-weight: bold; 
                padding: 6px 12px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        button_layout.addWidget(self.reset_button)

        button_layout.addStretch()

        # Apply Filter tlačítko
        self.apply_button = QPushButton("Apply Filter")
        self.apply_button.clicked.connect(self._apply_filter)
        self.apply_button.setStyleSheet("""
            QPushButton {
                background-color: #fd7e14; 
                color: white; 
                font-weight: bold; 
                padding: 6px 12px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #e76500;
            }
        """)
        button_layout.addWidget(self.apply_button)

        # Assign tlačítko
        self.assign_button = QPushButton("Assign")
        self.assign_button.clicked.connect(self._assign_velocity)
        self.assign_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745; 
                color: white; 
                font-weight: bold; 
                padding: 6px 12px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        button_layout.addWidget(self.assign_button)

        layout.addLayout(button_layout)

    def set_amplitude_data(self, samples: List[SampleMetadata], range_info: dict):
        """Nastaví amplitude data a rozsah"""
        self.samples = samples
        self.filter_settings.update_from_range_info(range_info)
        self.update_display()
        self._update_sliders()

    def _update_sliders(self):
        """Aktualizuje rozsah a hodnoty posuvníků"""
        if self.filter_settings.global_max <= self.filter_settings.global_min:
            return

        # Nastavení rozsahu spinboxů
        self.min_spinbox.setMinimum(self.filter_settings.global_min)
        self.min_spinbox.setMaximum(self.filter_settings.global_max)
        self.max_spinbox.setMinimum(self.filter_settings.global_min)
        self.max_spinbox.setMaximum(self.filter_settings.global_max)

        # Nastavení hodnot
        self.min_spinbox.setValue(self.filter_settings.filter_min)
        self.max_spinbox.setValue(self.filter_settings.filter_max)

        # Aktualizace sliderů
        self._update_slider_from_spinbox()

    def _update_slider_from_spinbox(self):
        """Aktualizuje slidery podle spinboxů"""
        if self.filter_settings.global_max <= self.filter_settings.global_min:
            return

        range_size = self.filter_settings.global_max - self.filter_settings.global_min

        # Min slider
        min_ratio = (self.filter_settings.filter_min - self.filter_settings.global_min) / range_size
        self.min_slider.blockSignals(True)
        self.min_slider.setValue(int(min_ratio * 10000))
        self.min_slider.blockSignals(False)

        # Max slider
        max_ratio = (self.filter_settings.filter_max - self.filter_settings.global_min) / range_size
        self.max_slider.blockSignals(True)
        self.max_slider.setValue(int(max_ratio * 10000))
        self.max_slider.blockSignals(False)

    def _on_min_slider_changed(self, value):
        """Handler pro změnu min slideru"""
        if self.filter_settings.global_max <= self.filter_settings.global_min:
            return

        range_size = self.filter_settings.global_max - self.filter_settings.global_min
        ratio = value / 10000.0
        new_min = self.filter_settings.global_min + ratio * range_size

        self.filter_settings.filter_min = new_min

        self.min_spinbox.blockSignals(True)
        self.min_spinbox.setValue(new_min)
        self.min_spinbox.blockSignals(False)

        # Zajisti že min <= max
        if self.filter_settings.filter_min > self.filter_settings.filter_max:
            self.filter_settings.filter_max = self.filter_settings.filter_min
            self.max_spinbox.setValue(self.filter_settings.filter_max)
            self._update_slider_from_spinbox()

        self._update_valid_samples_count()

    def _on_max_slider_changed(self, value):
        """Handler pro změnu max slideru"""
        if self.filter_settings.global_max <= self.filter_settings.global_min:
            return

        range_size = self.filter_settings.global_max - self.filter_settings.global_min
        ratio = value / 10000.0
        new_max = self.filter_settings.global_min + ratio * range_size

        self.filter_settings.filter_max = new_max

        self.max_spinbox.blockSignals(True)
        self.max_spinbox.setValue(new_max)
        self.max_spinbox.blockSignals(False)

        # Zajisti že min <= max
        if self.filter_settings.filter_min > self.filter_settings.filter_max:
            self.filter_settings.filter_min = self.filter_settings.filter_max
            self.min_spinbox.setValue(self.filter_settings.filter_min)
            self._update_slider_from_spinbox()

        self._update_valid_samples_count()

    def _on_min_spinbox_changed(self, value):
        """Handler pro změnu min spinboxu"""
        self.filter_settings.filter_min = value

        # Zajisti že min <= max
        if self.filter_settings.filter_min > self.filter_settings.filter_max:
            self.filter_settings.filter_max = self.filter_settings.filter_min
            self.max_spinbox.setValue(self.filter_settings.filter_max)

        self._update_slider_from_spinbox()
        self._update_valid_samples_count()

    def _on_max_spinbox_changed(self, value):
        """Handler pro změnu max spinboxu"""
        self.filter_settings.filter_max = value

        # Zajisti že min <= max
        if self.filter_settings.filter_min > self.filter_settings.filter_max:
            self.filter_settings.filter_min = self.filter_settings.filter_max
            self.min_spinbox.setValue(self.filter_settings.filter_min)

        self._update_slider_from_spinbox()
        self._update_valid_samples_count()

    def _update_valid_samples_count(self):
        """Aktualizuje počet validních samples"""
        if not self.samples:
            self.filter_settings.valid_samples = 0
        else:
            valid_count = 0
            for sample in self.samples:
                if (sample.peak_amplitude is not None and
                        self.filter_settings.is_in_range(sample.peak_amplitude)):
                    valid_count += 1
            self.filter_settings.valid_samples = valid_count

        self._update_samples_label()

    def _update_samples_label(self):
        """Aktualizuje label s počtem samples"""
        valid = self.filter_settings.valid_samples
        total = self.filter_settings.total_samples
        percentage = (valid / total * 100) if total > 0 else 0

        color = "#28a745" if percentage >= 80 else "#fd7e14" if percentage >= 50 else "#dc3545"

        self.samples_label.setText(f"Valid samples: {valid}/{total} ({percentage:.0f}%)")
        self.samples_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11px;")

    def _reset_to_full_range(self):
        """Reset na plný rozsah"""
        self.filter_settings.filter_min = self.filter_settings.global_min
        self.filter_settings.filter_max = self.filter_settings.global_max
        self._update_sliders()
        self._update_valid_samples_count()

    def _apply_filter(self):
        """Aplikuje filtr - označí samples šedou barvou"""
        # Emit signál s aktuálním nastavením
        self.filter_applied.emit(self.filter_settings)

    def _assign_velocity(self):
        """Přiřadí velocity levels"""
        # Emit signál pro přiřazení velocity
        self.velocity_assigned.emit(self.filter_settings)

    def update_display(self):
        """Aktualizuje všechny display elementy"""
        # Range label
        if self.filter_settings.total_samples == 0:
            self.range_label.setText("Detected range: No data")
            self.stats_label.setText("Statistics: No data")
        else:
            self.range_label.setText(
                f"Detected range: {self.filter_settings.global_min:.6f} - {self.filter_settings.global_max:.6f}"
            )

            self.stats_label.setText(
                f"Mean: {self.filter_settings.mean_amplitude:.6f}, "
                f"Std: {self.filter_settings.std_amplitude:.6f}, "
                f"P5-P95: {self.filter_settings.percentile_5:.6f} - {self.filter_settings.percentile_95:.6f}"
            )

        # Samples label
        self._update_samples_label()

        # Enable/disable controls
        has_data = self.filter_settings.total_samples > 0
        self.min_slider.setEnabled(has_data)
        self.max_slider.setEnabled(has_data)
        self.min_spinbox.setEnabled(has_data)
        self.max_spinbox.setEnabled(has_data)
        self.reset_button.setEnabled(has_data)
        self.apply_button.setEnabled(has_data)
        self.assign_button.setEnabled(has_data)

    def get_filter_settings(self) -> AmplitudeFilterSettings:
        """Vrátí aktuální nastavení filtru"""
        return self.filter_settings