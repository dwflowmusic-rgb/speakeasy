
import sys
import os
import pytest
from PySide6.QtWidgets import QApplication, QListWidget, QStackedWidget, QLabel, QPushButton
from PySide6.QtCore import Qt

from ui.janela_historico import JanelaHistorico
from core.historico import GerenciadorHistorico

# Ensure QApplication exists
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

def test_janela_historico_empty_state_and_tooltips(tmp_path):
    # Setup
    db_path = tmp_path / "test_historico.db"
    gerenciador = GerenciadorHistorico(str(db_path))

    janela = JanelaHistorico(gerenciador)

    # 1. Verify QStackedWidget is used
    stack_widgets = janela.findChildren(QStackedWidget)
    assert len(stack_widgets) > 0, "Should have QStackedWidget"
    stack = stack_widgets[0]

    # 2. Verify Initial State (Empty)
    # List is empty, so stack should show index 1 (Empty State)
    assert janela._lista.count() == 0
    assert stack.currentIndex() == 1, "Should show empty state (index 1) when no records"

    # 3. Verify Tooltips
    assert janela._btn_copiar.toolTip() != "", "Copy button should have tooltip"
    assert "área de transferência" in janela._btn_copiar.toolTip()

    assert janela._btn_excluir.toolTip() != "", "Delete button should have tooltip"
    assert "permanentemente" in janela._btn_excluir.toolTip()

    assert janela._btn_limpar_tudo.toolTip() != "", "Clear All button should have tooltip"

    # 4. Add data and verify state switch
    gerenciador.salvar(
        texto_bruto="Test raw",
        texto_polido="Test polished",
        duracao_segundos=1.5
    )

    janela.atualizar_lista()

    assert janela._lista.count() == 1
    assert stack.currentIndex() == 0, "Should show list (index 0) when records exist"

    janela.close()
