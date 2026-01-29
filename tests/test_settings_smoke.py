
"""
Smoke test for Settings Window.
"""
import pytest
from PySide6.QtWidgets import QApplication
from ui.janela_configuracoes import JanelaConfiguracoes

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

def test_settings_init(qapp):
    """Verify Settings Window initializes without error."""
    fake_config = {
        "transcription": {"model": "gemini-1.5-flash"},
        "polishing": {"model": "gpt-4o"},
        "api_keys": {"google": "fake", "openai": "fake"},
        "history": {"retention_days": 5}
    }
    window = JanelaConfiguracoes(fake_config)
    assert window is not None
    assert window.windowTitle() == "VoiceFlow - Configurações"
    window.close()
