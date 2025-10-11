"""
JsonSessionRepository - JSON-based persistence pro sessions.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.domain.interfaces import ISessionRepository

logger = logging.getLogger(__name__)


class JsonSessionRepository(ISessionRepository):
    """
    Implementace ISessionRepository pouzivajici JSON soubory.
    """

    def __init__(self, sessions_folder: Path = None):
        """
        Inicializuje repository.
        
        Args:
            sessions_folder: Slozka pro ukladani sessions (default: ./sessions)
        """
        self.sessions_folder = sessions_folder or Path("sessions")
        self.sessions_folder.mkdir(exist_ok=True)
        logger.info(f"JsonSessionRepository initialized: {self.sessions_folder}")

    def create(self, session_name: str) -> Dict[str, Any]:
        """Vytvori novou session."""
        if self.exists(session_name):
            raise ValueError(f"Session {session_name} already exists")

        session_data = {
            "session_name": session_name,
            "created": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            "folders": {
                "input": None,
                "output": None
            },
            "samples_cache": {},
            "mapping": {},
            "settings": {
                "amplitude_filter": None,
                "ui_state": {}
            }
        }

        self.save(session_name, session_data)
        logger.info(f"Created new session: {session_name}")
        return session_data

    def load(self, session_name: str) -> Optional[Dict[str, Any]]:
        """Nacte existujici session."""
        session_file = self._get_session_file(session_name)

        if not session_file.exists():
            logger.error(f"Session file not found: {session_file}")
            return None

        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            # Update last access time
            session_data["last_modified"] = datetime.now().isoformat()
            self.save(session_name, session_data)

            logger.info(f"Loaded session: {session_name}")
            return session_data

        except Exception as e:
            logger.error(f"Failed to load session {session_name}: {e}")
            return None

    def save(self, session_name: str, session_data: Dict[str, Any]) -> bool:
        """Ulozi session data."""
        session_file = self._get_session_file(session_name)

        try:
            # Backup existujici soubor
            if session_file.exists():
                backup_file = session_file.with_suffix('.json.backup')
                session_file.replace(backup_file)

            # Update timestamp
            session_data["last_modified"] = datetime.now().isoformat()

            # Save
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Session saved: {session_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save session {session_name}: {e}")

            # Pokus o obnoveni z backup
            backup_file = session_file.with_suffix('.json.backup')
            if backup_file.exists():
                backup_file.replace(session_file)
                logger.info("Restored session from backup after save failure")

            return False

    def exists(self, session_name: str) -> bool:
        """Kontroluje zda session existuje."""
        return self._get_session_file(session_name).exists()

    def list_sessions(self) -> List[str]:
        """Vrati seznam vsech dostupnych sessions."""
        session_files = list(self.sessions_folder.glob("session-*.json"))
        session_names = []

        for file_path in session_files:
            # Extrahuj nazev ze souboru session-<name>.json
            name = file_path.stem[8:]  # Odstran "session-" prefix
            session_names.append(name)

        return sorted(session_names)

    def delete(self, session_name: str) -> bool:
        """Smaze session."""
        session_file = self._get_session_file(session_name)

        if not session_file.exists():
            return False

        try:
            session_file.unlink()
            logger.info(f"Deleted session: {session_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_name}: {e}")
            return False

    def _get_session_file(self, session_name: str) -> Path:
        """Vrati cestu k session souboru."""
        return self.sessions_folder / f"session-{session_name}.json"
