"""
Unit testy pro SessionPresenter.
"""

import pytest
from unittest.mock import Mock

from src.presentation.presenters.session_presenter import SessionPresenter


@pytest.mark.unit
class TestSessionPresenter:
    """Testy pro SessionPresenter."""

    def test_initialization(self):
        """Test inicializace presenteru."""
        presenter = SessionPresenter()
        assert presenter is not None
        assert presenter.session_service is not None
        assert presenter.current_session_name is None

    def test_get_current_session_name(self):
        """Test získání jména session."""
        presenter = SessionPresenter()
        assert presenter.get_current_session_name() is None
        
        presenter.current_session_name = 'test_session'
        assert presenter.get_current_session_name() == 'test_session'
