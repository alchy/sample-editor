"""
session_dialog.py - Startup dialog pro session management
"""

from typing import Optional
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QListWidget, QLineEdit, QGroupBox, QMessageBox, QFrame, QSpinBox,
                               QTextEdit, QScrollArea, QWidget)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import QListWidgetItem

from config import AUDIO, GUI
from session_manager import SessionManager
import logging

logger = logging.getLogger(__name__)


class SessionDialog(QDialog):
    """Dialog pro výběr nebo vytvoření session."""

    def __init__(self, session_manager: SessionManager, parent=None):
        super().__init__(parent)
        self.session_manager = session_manager
        self.selected_session = None
        self.is_new_session = False

        self.setWindowTitle(GUI.Texts.SESSION_DIALOG_TITLE)
        self.setModal(True)
        self.resize(800, 600)  # Zvětšeno pro nové metadata fieldy

        self.init_ui()
        self.refresh_sessions_list()

    def init_ui(self):
        """Inicializuje UI dialogu."""
        layout = QVBoxLayout()

        # Header
        header_label = QLabel(GUI.Texts.SESSION_HEADER)
        header_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet("color: #2c3e50; margin: 10px;")
        layout.addWidget(header_label)

        subtitle_label = QLabel(GUI.Texts.SESSION_SUBTITLE)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #7f8c8d; margin-bottom: 20px;")
        layout.addWidget(subtitle_label)

        # Main content - horizontal split
        main_layout = QHBoxLayout()

        # Left side - Recent Sessions
        self._create_recent_sessions_section(main_layout)

        # Vertical separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("color: #bdc3c7;")
        main_layout.addWidget(separator)

        # Right side - New Session
        self._create_new_session_section(main_layout)

        layout.addLayout(main_layout)

        # Bottom buttons
        self._create_bottom_buttons(layout)

        self.setLayout(layout)

    def _create_recent_sessions_section(self, main_layout):
        """Vytvoří sekci s recent sessions."""
        left_group = QGroupBox("Nedávné Sessions")
        left_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 5px 0 5px;
                color: #3498db;
            }
        """)
        left_layout = QVBoxLayout()

        # Sessions list
        self.sessions_list = QListWidget()
        self.sessions_list.setMinimumHeight(200)
        self.sessions_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: #ffffff;
                selection-background-color: #3498db;
                selection-color: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #ecf0f1;
            }
            QListWidget::item:hover {
                background-color: #f8f9fa;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        self.sessions_list.itemDoubleClicked.connect(self._on_session_double_click)
        self.sessions_list.itemSelectionChanged.connect(self._on_session_selection_changed)
        left_layout.addWidget(self.sessions_list)

        # Load button
        self.btn_load_session = QPushButton("Načíst Session")
        self.btn_load_session.setEnabled(False)
        self.btn_load_session.clicked.connect(self._load_selected_session)
        self.btn_load_session.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        left_layout.addWidget(self.btn_load_session)

        left_group.setLayout(left_layout)
        main_layout.addWidget(left_group)

    def _create_new_session_section(self, main_layout):
        """Vytvoří sekci pro novou session."""
        right_group = QGroupBox("Nová Session")
        right_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #27ae60;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 5px 0 5px;
                color: #27ae60;
            }
        """)
        right_layout = QVBoxLayout()

        # Instructions
        instruction_label = QLabel("Zadejte název pro novou session:")
        instruction_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        right_layout.addWidget(instruction_label)

        # Session name input
        self.session_name_input = QLineEdit()
        self.session_name_input.setPlaceholderText("např. drums_2024, vocals_project...")
        self.session_name_input.textChanged.connect(self._on_session_name_changed)
        self.session_name_input.returnPressed.connect(self._create_new_session)
        self.session_name_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #27ae60;
            }
        """)
        right_layout.addWidget(self.session_name_input)

        # Velocity Layers input
        velocity_label = QLabel("Počet velocity layers:")
        velocity_label.setStyleSheet("color: #2c3e50; margin-top: 10px; margin-bottom: 5px;")
        right_layout.addWidget(velocity_label)

        velocity_layout = QHBoxLayout()
        self.velocity_layers_spinbox = QSpinBox()
        self.velocity_layers_spinbox.setRange(AUDIO.Velocity.MIN_LAYERS, AUDIO.Velocity.MAX_LAYERS)
        self.velocity_layers_spinbox.setValue(AUDIO.Velocity.DEFAULT_LAYERS)
        self.velocity_layers_spinbox.setToolTip(f"Počet velocity vrstev v mapovací matici ({AUDIO.Velocity.MIN_LAYERS}-{AUDIO.Velocity.MAX_LAYERS})")
        self.velocity_layers_spinbox.setStyleSheet("""
            QSpinBox {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
                font-size: 12px;
                min-width: 60px;
            }
            QSpinBox:focus {
                border-color: #27ae60;
            }
        """)
        velocity_layout.addWidget(self.velocity_layers_spinbox)

        velocity_info = QLabel(f"({AUDIO.Velocity.MIN_LAYERS} = jeden layer, {AUDIO.Velocity.DEFAULT_LAYERS} = výchozí, {AUDIO.Velocity.MAX_LAYERS} = maximum)")
        velocity_info.setStyleSheet("color: #7f8c8d; font-size: 9px;")
        velocity_layout.addWidget(velocity_info)
        velocity_layout.addStretch()

        right_layout.addLayout(velocity_layout)

        # === INSTRUMENT METADATA (pro export JSON) ===

        # Instrument Name
        instrument_name_label = QLabel("Instrument Name:")
        instrument_name_label.setStyleSheet("color: #2c3e50; margin-top: 10px; margin-bottom: 5px; font-weight: bold;")
        right_layout.addWidget(instrument_name_label)

        self.instrument_name_input = QLineEdit()
        self.instrument_name_input.setPlaceholderText("např. Steinway Grand Piano (volitelné - default: session name)")
        self.instrument_name_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #27ae60;
            }
        """)
        right_layout.addWidget(self.instrument_name_input)

        # Author
        author_label = QLabel("Author:")
        author_label.setStyleSheet("color: #2c3e50; margin-top: 10px; margin-bottom: 5px;")
        right_layout.addWidget(author_label)

        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("např. John Doe, Studio XYZ (volitelné)")
        self.author_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #27ae60;
            }
        """)
        right_layout.addWidget(self.author_input)

        # Category
        category_label = QLabel("Category:")
        category_label.setStyleSheet("color: #2c3e50; margin-top: 10px; margin-bottom: 5px;")
        right_layout.addWidget(category_label)

        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("např. Piano, Drums, Synth (volitelné)")
        self.category_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #27ae60;
            }
        """)
        right_layout.addWidget(self.category_input)

        # Description
        description_label = QLabel("Description:")
        description_label.setStyleSheet("color: #2c3e50; margin-top: 10px; margin-bottom: 5px;")
        right_layout.addWidget(description_label)

        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Popis nástroje... (volitelné)")
        self.description_input.setMaximumHeight(60)
        self.description_input.setStyleSheet("""
            QTextEdit {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
                font-size: 12px;
            }
            QTextEdit:focus {
                border-color: #27ae60;
            }
        """)
        right_layout.addWidget(self.description_input)

        # Validation info
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("color: #e74c3c; font-size: 10px; margin-top: 5px;")
        right_layout.addWidget(self.validation_label)

        # Spacer - menší kvůli novým fieldům
        right_layout.addStretch()

        # Create button
        self.btn_create_session = QPushButton("Vytvořit Session")
        self.btn_create_session.setEnabled(False)
        self.btn_create_session.clicked.connect(self._create_new_session)
        self.btn_create_session.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        right_layout.addWidget(self.btn_create_session)

        right_group.setLayout(right_layout)
        main_layout.addWidget(right_group)

    def _create_bottom_buttons(self, layout):
        """Vytvoří spodní tlačítka."""
        bottom_layout = QHBoxLayout()

        # Info label
        info_label = QLabel("Session soubory jsou uloženy v složce 'sessions'")
        info_label.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        bottom_layout.addWidget(info_label)

        bottom_layout.addStretch()

        # Exit button
        btn_exit = QPushButton("Ukončit")
        btn_exit.clicked.connect(self.reject)
        btn_exit.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 8px 20px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        bottom_layout.addWidget(btn_exit)

        layout.addLayout(bottom_layout)

    def refresh_sessions_list(self):
        """Obnoví seznam sessions."""
        self.sessions_list.clear()

        try:
            sessions = self.session_manager.get_available_sessions()

            if not sessions:
                # Přidej placeholder item
                placeholder_item = QListWidgetItem("Žádné sessions nenalezeny.\nVytvořte novou session vpravo.")
                placeholder_item.setFlags(placeholder_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                placeholder_item.setForeground(QColor("#7f8c8d"))
                self.sessions_list.addItem(placeholder_item)
            else:
                for session_name in sessions:
                    self.sessions_list.addItem(session_name)

        except Exception as e:
            logger.error(f"Failed to refresh sessions list: {e}")
            QMessageBox.critical(self, "Chyba", f"Nelze načíst seznam sessions:\n{e}")

    def _on_session_selection_changed(self):
        """Handler pro změnu výběru session."""
        selected_items = self.sessions_list.selectedItems()
        self.btn_load_session.setEnabled(len(selected_items) > 0)

    def _on_session_double_click(self, item):
        """Handler pro double-click na session."""
        self._load_selected_session()

    def _on_session_name_changed(self, text: str):
        """Handler pro změnu názvu nové session."""
        is_valid = self._validate_session_name(text)
        self.btn_create_session.setEnabled(is_valid)

    def _validate_session_name(self, name: str) -> bool:
        """Validuje název session."""
        if not name.strip():
            self.validation_label.setText("")
            return False

        # Check for invalid characters
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in name for char in invalid_chars):
            self.validation_label.setText("Název obsahuje nepovolené znaky")
            return False

        # Check if session already exists
        try:
            existing_sessions = self.session_manager.get_available_sessions()
            if name.lower() in [s.lower() for s in existing_sessions]:
                self.validation_label.setText("Session s tímto názvem již existuje")
                return False
        except Exception as e:
            logger.error(f"Error checking existing sessions: {e}")
            self.validation_label.setText("Chyba při kontrole existujících sessions")
            return False

        self.validation_label.setText("")
        return True

    def _load_selected_session(self):
        """Načte vybranou session."""
        selected_items = self.sessions_list.selectedItems()
        if not selected_items:
            return

        session_name = selected_items[0].text()

        try:
            if self.session_manager.load_session(session_name):
                self.selected_session = session_name
                self.is_new_session = False
                self.accept()
                logger.info(f"Session selected for loading: {session_name}")
            else:
                QMessageBox.critical(self, "Chyba", f"Nelze načíst session '{session_name}'")

        except Exception as e:
            logger.error(f"Failed to load session {session_name}: {e}")
            QMessageBox.critical(self, "Chyba", f"Chyba při načítání session:\n{e}")

    def _create_new_session(self):
        """Vytvoří novou session s metadaty."""
        session_name = self.session_name_input.text().strip()

        if not self._validate_session_name(session_name):
            return

        try:
            # Získej všechna metadata
            velocity_layers = self.velocity_layers_spinbox.value()

            # Instrument name - pokud není zadán, použij session name
            instrument_name = self.instrument_name_input.text().strip() or session_name

            author = self.author_input.text().strip() or "N/A"
            category = self.category_input.text().strip() or "N/A"
            description = self.description_input.toPlainText().strip() or "N/A"

            # Metadata dictionary pro JSON export
            metadata = {
                'instrument_name': instrument_name,
                'author': author,
                'category': category,
                'description': description,
            }

            if self.session_manager.create_new_session(session_name,
                                                      velocity_layers=velocity_layers,
                                                      metadata=metadata):
                self.selected_session = session_name
                self.is_new_session = True
                self.accept()
                logger.info(f"New session created: {session_name} with {velocity_layers} velocity layers")
                logger.info(f"Instrument metadata - Name: {instrument_name}, Author: {author}, Category: {category}")
            else:
                QMessageBox.critical(self, "Chyba", f"Session '{session_name}' již existuje")

        except Exception as e:
            logger.error(f"Failed to create session {session_name}: {e}")
            QMessageBox.critical(self, "Chyba", f"Chyba při vytváření session:\n{e}")

    def get_selected_session(self) -> Optional[str]:
        """Vrátí název vybrané session."""
        return self.selected_session

    def is_new_session_created(self) -> bool:
        """Vrátí True pokud byla vytvořena nová session."""
        return self.is_new_session