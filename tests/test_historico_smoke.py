"""
Smoke test for History Window.
"""
import pytest
from PySide6.QtWidgets import QApplication
from ui.janela_historico import JanelaHistorico
from core.historico import GerenciadorHistorico
from unittest.mock import MagicMock

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

def test_historico_init_empty(qapp):
    """Verify History Window initializes with empty list (Empty State)."""
    # Mock manager to return empty list
    mock_manager = MagicMock(spec=GerenciadorHistorico)
    mock_manager.listar.return_value = []
    mock_manager.contar.return_value = 0

    window = JanelaHistorico(gerenciador=mock_manager)

    # Check if empty state is shown (index 1)
    assert window._stacked_widget.currentIndex() == 1

    # Verify the widget at index 1 is indeed the empty state widget
    assert window._stacked_widget.currentWidget() == window._widget_vazio

    window.close()

def test_historico_init_with_data(qapp):
    """Verify History Window initializes with data (List State)."""
    # Mock manager to return some data
    mock_manager = MagicMock(spec=GerenciadorHistorico)

    # Mock a record
    mock_record = MagicMock()
    mock_record.id = 1
    mock_record.timestamp_formatado = "01/01/2026 10:00"
    mock_record.duracao_segundos = 5.0
    mock_record.preview = "Test preview..."

    mock_manager.listar.return_value = [mock_record]
    mock_manager.contar.return_value = 1

    window = JanelaHistorico(gerenciador=mock_manager)

    # Check if list state is shown (index 0)
    assert window._stacked_widget.currentIndex() == 0

    # Verify the widget at index 0 is indeed the list widget
    assert window._stacked_widget.currentWidget() == window._lista

    window.close()
