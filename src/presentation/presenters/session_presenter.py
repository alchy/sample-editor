"""
SessionPresenter - Presentation logic for session management.

Zodpovědnosti:
- Správa session lifecycle (create, load, save)
- Session persistence přes SessionService
- Koordinace session state s view
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from PySide6.QtCore import QObject, Signal

from src.domain.models.sample import SampleMetadata
from src.application.services.session_service import SessionService
from src.infrastructure.persistence.session_repository_impl import JsonSessionRepository
from src.infrastructure.persistence.cache_manager import Md5CacheManager

logger = logging.getLogger(__name__)


class SessionPresenter(QObject):
    """
    Prezentér pro správu sessions.
    
    Odděluje business logiku session managementu od GUI.
    """
    
    # Signály
    session_created = Signal(str)  # session_name
    session_loaded = Signal(str, dict)  # session_name, session_info
    session_saved = Signal()
    session_error = Signal(str)  # error message
    
    def __init__(self, session_service: Optional[SessionService] = None):
        """
        Args:
            session_service: Optional SessionService, vytvoří se default pokud None
        """
        super().__init__()
        
        # Dependency injection nebo vytvoření default service
        if session_service is None:
            repository = JsonSessionRepository()
            cache_manager = Md5CacheManager()
            self.session_service = SessionService(repository, cache_manager)
        else:
            self.session_service = session_service
        
        self.current_session_name: Optional[str] = None
    
    def create_session(self, session_name: str) -> bool:
        """
        Vytvoří novou session.
        
        Args:
            session_name: Jméno nové session
            
        Returns:
            True pokud byla session úspěšně vytvořena
        """
        try:
            # Zavři aktuální session pokud existuje
            if self.current_session_name:
                self.close_session()
            
            # Vytvoř novou session
            session_data = self.session_service.create_session(session_name)
            self.current_session_name = session_name
            
            logger.info(f"Session created: {session_name}")
            self.session_created.emit(session_name)
            return True
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            self.session_error.emit(str(e))
            return False
    
    def load_session(self, session_name: str) -> bool:
        """
        Načte existující session.
        
        Args:
            session_name: Jméno session k načtení
            
        Returns:
            True pokud byla session úspěšně načtena
        """
        try:
            # Zavři aktuální session pokud existuje
            if self.current_session_name:
                self.close_session()
            
            # Načti session
            success = self.session_service.load_session(session_name)
            
            if success:
                self.current_session_name = session_name
                session_info = self.get_session_info()
                
                logger.info(f"Session loaded: {session_name}")
                self.session_loaded.emit(session_name, session_info)
                return True
            else:
                self.session_error.emit(f"Failed to load session: {session_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            self.session_error.emit(str(e))
            return False
    
    def save_session(self) -> bool:
        """
        Uloží aktuální session.
        
        Returns:
            True pokud byla session úspěšně uložena
        """
        try:
            if not self.current_session_name:
                self.session_error.emit("No active session to save")
                return False
            
            success = self.session_service.save_session()
            
            if success:
                logger.info(f"Session saved: {self.current_session_name}")
                self.session_saved.emit()
                return True
            else:
                self.session_error.emit("Failed to save session")
                return False
                
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            self.session_error.emit(str(e))
            return False
    
    def close_session(self):
        """Zavře aktuální session (uloží před zavřením)."""
        if self.current_session_name:
            self.save_session()
            self.current_session_name = None
            logger.info("Session closed")
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        Vrátí informace o aktuální session.
        
        Returns:
            Dictionary s session info
        """
        if not self.current_session_name:
            return {}
        
        cache_stats = self.session_service.cache.get_stats()
        
        return {
            'name': self.current_session_name,
            'cached_samples': cache_stats.get('total_entries', 0),
            'mapping_entries': len(self.session_service.session_data.get('mapping', {})) if self.session_service.session_data else 0
        }
    
    def list_sessions(self) -> List[str]:
        """
        Vrátí seznam všech dostupných sessions.
        
        Returns:
            List jmen sessions
        """
        try:
            return self.session_service.repository.list_sessions()
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []
    
    def get_current_session_name(self) -> Optional[str]:
        """Vrátí jméno aktuální session."""
        return self.current_session_name
