# -*- coding: utf-8 -*-
"""
Ícone de Bandeja (System Tray) do VoiceFlow Transcriber.

Interface mínima: ícone discreto com menu de contexto.
Sem janela principal visível durante operação normal.
"""

import sys
import os
from typing import Optional, Callable

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QStyle
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QTimer

from core.logger import obter_logger

logger = obter_logger('icone_bandeja')

# Caminho do ícone (usa ícone padrão se não encontrar)
CAMINHO_ICONE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 
    'resources', 
    'icon.ico'
)


class IconeBandeja:
    """
    Gerencia ícone na bandeja do sistema (system tray).
    
    Fornece menu de contexto com opções:
    - Ver Histórico (Fase 2)
    - Configurações (Fase 3)
    - Sair
    """
    
    def __init__(self, app: QApplication):
        """
        Inicializa ícone na bandeja.
        
        Args:
            app: Instância da aplicação Qt
        """
        self._app = app
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._menu: Optional[QMenu] = None
        
        # Callbacks para ações do menu
        self._callback_historico: Optional[Callable] = None
        self._callback_configuracoes: Optional[Callable] = None
        self._callback_autostart: Optional[Callable[[bool], None]] = None
        self._callback_auto_enter: Optional[Callable[[bool], None]] = None
        self._callback_retry: Optional[Callable] = None
        self._callback_sair: Optional[Callable] = None
        
        self._criar_tray_icon()
    
    def _criar_tray_icon(self) -> None:
        """Cria e configura ícone na bandeja."""
        # Configura ícone
        if os.path.exists(CAMINHO_ICONE):
            icone = QIcon(CAMINHO_ICONE)
        else:
            # Fallback: Ícone padrão do sistema
            logger.warning(f"Ícone personalizado não encontrado em {CAMINHO_ICONE}. Usando padrão.")
            style = QApplication.style()
            icone = style.standardIcon(QStyle.SP_ComputerIcon)
        
        self._tray_icon = QSystemTrayIcon(icone, self._app)
        self._tray_icon.setToolTip("VoiceFlow Transcriber")
        
        # Cria menu de contexto
        self._menu = QMenu()
        
        # Ação: Status (apenas informativos)
        acao_status = QAction("🎤 VoiceFlow Transcriber", self._menu)
        acao_status.setEnabled(False)
        self._menu.addAction(acao_status)
        
        self._menu.addSeparator()
        
        # Ação: Ver Histórico (Fase 2 - desabilitado por enquanto)
        self._acao_historico = QAction("📋 Ver Histórico", self._menu)
        self._acao_historico.setEnabled(False)  # Habilitado na Fase 2
        self._acao_historico.triggered.connect(self._on_historico)
        self._menu.addAction(self._acao_historico)

        # Ação: Ver Falhas (NOVO)
        self._acao_retry = QAction("⚠️ Áudios Falhos", self._menu)
        self._acao_retry.setEnabled(False) 
        self._acao_retry.triggered.connect(self._on_retry)
        self._menu.addAction(self._acao_retry)
        
        # Ação: Configurações (Fase 3 - desabilitado por enquanto)
        self._acao_configuracoes = QAction("⚙️ Configurações", self._menu)
        self._acao_configuracoes.setEnabled(False)  # Habilitado na Fase 3
        self._acao_configuracoes.triggered.connect(self._on_configuracoes)
        self._menu.addAction(self._acao_configuracoes)
        
        # Ação: Iniciar com Windows (Checkable)
        self._acao_autostart = QAction("🚀 Iniciar com Windows", self._menu)
        self._acao_autostart.setCheckable(True)
        self._acao_autostart.triggered.connect(self._on_autostart)
        self._menu.addAction(self._acao_autostart)
        
        # Ação: Auto-Enter após Colar (Checkable)
        self._acao_auto_enter = QAction("↵ Auto-Enter após Colar", self._menu)
        self._acao_auto_enter.setCheckable(True)
        self._acao_auto_enter.triggered.connect(self._on_auto_enter)
        self._menu.addAction(self._acao_auto_enter)
        
        self._menu.addSeparator()
        
        # Ação: Sair
        acao_sair = QAction("❌ Sair", self._menu)
        acao_sair.triggered.connect(self._on_sair)
        self._menu.addAction(acao_sair)
        
        self._tray_icon.setContextMenu(self._menu)
        self._tray_icon.show()
        
        logger.info("Ícone na bandeja criado e visível")
    
    def _on_historico(self) -> None:
        """Handler para ação Ver Histórico."""
        if self._callback_historico:
            self._callback_historico()
    
    def _on_configuracoes(self) -> None:
        """Handler para ação Configurações."""
        if self._callback_configuracoes:
            self._callback_configuracoes()
    
    def _on_autostart(self, checked: bool) -> None:
        """Handler para alteração do autostart."""
        if self._callback_autostart:
            self._callback_autostart(checked)
    
    def _on_auto_enter(self, checked: bool) -> None:
        """Handler para alteração do auto-enter."""
        if self._callback_auto_enter:
            self._callback_auto_enter(checked)
    
    def _on_sair(self) -> None:
        """Handler para ação Sair."""
        logger.info("Usuário solicitou encerramento via menu")
        if self._callback_sair:
            self._callback_sair()
        self._tray_icon.hide()
        self._app.quit()

    def _on_retry(self) -> None:
        """Handler para ação Ver Falhas."""
        if self._callback_retry:
            self._callback_retry()
    
    def registrar_callback_historico(self, callback: Callable) -> None:
        """Registra callback para quando usuário clicar em Ver Histórico."""
        self._callback_historico = callback
        self._acao_historico.setEnabled(True)
    
    def registrar_callback_configuracoes(self, callback: Callable) -> None:
        """Registra callback para quando usuário clicar em Configurações."""
        self._callback_configuracoes = callback
        self._acao_configuracoes.setEnabled(True)

    def registrar_callback_retry(self, callback: Callable) -> None:
        """Registra callback para quando usuário clicar em Áudios Falhos."""
        self._callback_retry = callback
        self._acao_retry.setEnabled(True)
    
    def registrar_callback_autostart(self, callback: Callable[[bool], None]) -> None:
        """Registra callback para toggle de autostart."""
        self._callback_autostart = callback

    def definir_estado_autostart(self, ativado: bool) -> None:
        """Define estado visual do checkbox autostart."""
        block = self._acao_autostart.blockSignals(True)
        self._acao_autostart.setChecked(ativado)
        self._acao_autostart.blockSignals(block)
    
    def registrar_callback_auto_enter(self, callback: Callable[[bool], None]) -> None:
        """Registra callback para toggle de auto-enter."""
        self._callback_auto_enter = callback

    def definir_estado_auto_enter(self, ativado: bool) -> None:
        """Define estado visual do checkbox auto-enter."""
        block = self._acao_auto_enter.blockSignals(True)
        self._acao_auto_enter.setChecked(ativado)
        self._acao_auto_enter.blockSignals(block)
    
    def registrar_callback_sair(self, callback: Callable) -> None:
        """Registra callback para quando usuário clicar em Sair."""
        self._callback_sair = callback
    
    def atualizar_tooltip(self, texto: str) -> None:
        """Atualiza tooltip do ícone."""
        self._tray_icon.setToolTip(texto)
    
    def exibir_mensagem(self, titulo: str, mensagem: str) -> None:
        """Exibe mensagem balloon do system tray."""
        self._tray_icon.showMessage(titulo, mensagem, QSystemTrayIcon.Information, 3000)
