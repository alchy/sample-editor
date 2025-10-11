"""
Interface pro Session Repository - definuje kontrakt pro ukládání sessions.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path


class ISessionRepository(ABC):
    """
    Repository interface pro persistence session dat.
    Implementace může být JSON, SQL, Redis, atd.
    """

    @abstractmethod
    def create(self, session_name: str) -> Dict[str, Any]:
        """
        Vytvoří novou session.
        
        Args:
            session_name: Název session
            
        Returns:
            Session data dictionary
        """
        pass

    @abstractmethod
    def load(self, session_name: str) -> Optional[Dict[str, Any]]:
        """
        Načte existující session.
        
        Args:
            session_name: Název session
            
        Returns:
            Session data nebo None pokud neexistuje
        """
        pass

    @abstractmethod
    def save(self, session_name: str, session_data: Dict[str, Any]) -> bool:
        """
        Uloží session data.
        
        Args:
            session_name: Název session
            session_data: Data k uložení
            
        Returns:
            True pokud se podařilo uložit
        """
        pass

    @abstractmethod
    def exists(self, session_name: str) -> bool:
        """
        Kontroluje zda session existuje.
        
        Args:
            session_name: Název session
            
        Returns:
            True pokud existuje
        """
        pass

    @abstractmethod
    def list_sessions(self) -> List[str]:
        """
        Vrátí seznam všech dostupných sessions.
        
        Returns:
            Seznam názvů sessions
        """
        pass

    @abstractmethod
    def delete(self, session_name: str) -> bool:
        """
        Smaže session.
        
        Args:
            session_name: Název session
            
        Returns:
            True pokud se podařilo smazat
        """
        pass
