# -*- coding: utf-8 -*-
"""
Janela de Histórico do VoiceFlow Transcriber.

Interface Qt para visualização, busca e recuperação de transcrições anteriores.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QListWidget, QListWidgetItem, QTextEdit, QPushButton,
    QLabel, QSplitter, QWidget, QMessageBox, QStackedWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from core.historico import GerenciadorHistorico, RegistroTranscricao
from core.gerenciador_clipboard import copiar_para_clipboard
from core.logger import obter_logger

logger = obter_logger('janela_historico')


class JanelaHistorico(QDialog):
    """
    Janela para visualização do histórico de transcrições.
    
    Features:
    - Lista cronológica (mais recente primeiro)
    - Busca em tempo real
    - Visualização de texto completo
    - Cópia para clipboard
    """
    
    def __init__(self, gerenciador: Optional[GerenciadorHistorico] = None, parent=None):
        super().__init__(parent)
        self._historico = gerenciador if gerenciador else GerenciadorHistorico()
        self._registro_selecionado: Optional[RegistroTranscricao] = None
        
        self._configurar_janela()
        self._criar_widgets()
        self._configurar_layout()
        self._conectar_sinais()
        self.atualizar_lista()
    
    def _configurar_janela(self) -> None:
        """Configura propriedades da janela."""
        self.setWindowTitle("VoiceFlow - Histórico de Transcrições")
        self.setMinimumSize(800, 600)
        self.setModal(False)  # Permite interação com outras janelas
    
    def _criar_widgets(self) -> None:
        """Cria todos os widgets da interface."""
        # Busca
        self._lbl_busca = QLabel("🔍 Buscar:")
        self._txt_busca = QLineEdit()
        self._txt_busca.setPlaceholderText("Digite para filtrar transcrições...")
        self._txt_busca.setClearButtonEnabled(True)
        
        # Lista de transcrições
        self._lista = QListWidget()
        self._lista.setAlternatingRowColors(True)
        
        # Empty State (Widget vazio)
        self._widget_vazio = QWidget()
        layout_vazio = QVBoxLayout(self._widget_vazio)

        lbl_icone_vazio = QLabel("📭")
        lbl_icone_vazio.setAlignment(Qt.AlignCenter)
        font_emoji = QFont()
        font_emoji.setPointSize(48)
        lbl_icone_vazio.setFont(font_emoji)

        self._lbl_msg_vazio = QLabel("Nenhuma transcrição encontrada.\nSegure CapsLock para gravar.")
        self._lbl_msg_vazio.setAlignment(Qt.AlignCenter)
        self._lbl_msg_vazio.setStyleSheet("color: gray; font-size: 14px;")

        layout_vazio.addStretch()
        layout_vazio.addWidget(lbl_icone_vazio)
        layout_vazio.addWidget(self._lbl_msg_vazio)
        layout_vazio.addStretch()

        # Stack para alternar entre lista e vazio
        self._stack_lista = QStackedWidget()
        self._stack_lista.addWidget(self._lista)
        self._stack_lista.addWidget(self._widget_vazio)

        # Contador
        self._lbl_contador = QLabel("0 transcrições")
        
        # Painel de detalhes
        self._lbl_detalhes = QLabel("Selecione uma transcrição para ver detalhes")
        self._lbl_detalhes.setStyleSheet("color: gray; font-style: italic;")
        
        self._txt_polido = QTextEdit()
        self._txt_polido.setReadOnly(True)
        self._txt_polido.setPlaceholderText("Texto polido aparecerá aqui...")
        
        self._txt_bruto = QTextEdit()
        self._txt_bruto.setReadOnly(True)
        self._txt_bruto.setPlaceholderText("Texto bruto da transcrição...")
        self._txt_bruto.setMaximumHeight(100)
        
        # Botões
        self._btn_copiar = QPushButton("📋 Copiar para Clipboard")
        self._btn_copiar.setEnabled(False)
        
        self._btn_excluir = QPushButton("🗑️ Excluir")
        self._btn_excluir.setEnabled(False)
        self._btn_excluir.setStyleSheet("color: #c9302c;")
        
        self._btn_limpar_tudo = QPushButton("🧹 Limpar Histórico")
        self._btn_limpar_tudo.setStyleSheet("color: #c9302c; font-weight: bold;")
        
        self._btn_fechar = QPushButton("Fechar")
    
    def _configurar_layout(self) -> None:
        """Configura layout dos widgets."""
        # Layout de busca
        layout_busca = QHBoxLayout()
        layout_busca.addWidget(self._lbl_busca)
        layout_busca.addWidget(self._txt_busca)
        
        # Painel esquerdo (lista)
        widget_lista = QWidget()
        layout_lista = QVBoxLayout(widget_lista)
        layout_lista.setContentsMargins(0, 0, 0, 0)
        layout_lista.addLayout(layout_busca)
        layout_lista.addWidget(self._stack_lista)
        layout_lista.addWidget(self._lbl_contador)
        
        # Painel direito (detalhes)
        widget_detalhes = QWidget()
        layout_detalhes = QVBoxLayout(widget_detalhes)
        layout_detalhes.setContentsMargins(0, 0, 0, 0)
        layout_detalhes.addWidget(self._lbl_detalhes)
        layout_detalhes.addWidget(QLabel("📝 Texto Polido:"))
        layout_detalhes.addWidget(self._txt_polido, stretch=1)
        layout_detalhes.addWidget(QLabel("📄 Texto Bruto (original):"))
        layout_detalhes.addWidget(self._txt_bruto)
        
        layout_botoes_detalhe = QHBoxLayout()
        layout_botoes_detalhe.addWidget(self._btn_copiar, stretch=2)
        layout_botoes_detalhe.addWidget(self._btn_excluir, stretch=1)
        
        layout_detalhes.addLayout(layout_botoes_detalhe)
        
        # Splitter para redimensionamento
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(widget_lista)
        splitter.addWidget(widget_detalhes)
        splitter.setSizes([300, 500])
        
        # Botões inferiores
        layout_botoes = QHBoxLayout()
        layout_botoes.addWidget(self._btn_limpar_tudo)
        layout_botoes.addStretch()
        layout_botoes.addWidget(self._btn_fechar)
        
        # Layout principal
        layout_principal = QVBoxLayout(self)
        layout_principal.addWidget(splitter)
        layout_principal.addLayout(layout_botoes)
    
    def _conectar_sinais(self) -> None:
        """Conecta sinais aos slots."""
        self._txt_busca.textChanged.connect(self._on_busca_alterada)
        self._lista.currentItemChanged.connect(self._on_item_selecionado)
        self._btn_copiar.clicked.connect(self._on_copiar_clicado)
        self._btn_excluir.clicked.connect(self._on_excluir_clicado)
        self._btn_limpar_tudo.clicked.connect(self._on_limpar_tudo_clicado)
        self._btn_fechar.clicked.connect(self.close)
    
    def atualizar_lista(self, termo_busca: str = "") -> None:
        """
        Carrega/Atualiza lista de transcrições.
        Pode ser chamado externamente para auto-refresh.
        
        Args:
            termo_busca: Termo para filtrar (vazio = todos)
        """
        self._lista.clear()
        
        if termo_busca:
            registros = self._historico.buscar(termo_busca)
        else:
            registros = self._historico.listar(limite=100)
        
        for registro in registros:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, registro.id)
            
            # Formata texto do item
            texto = (
                f"📅 {registro.timestamp_formatado} "
                f"({registro.duracao_segundos:.1f}s)\n"
                f"   {registro.preview}"
            )
            item.setText(texto)
            
            self._lista.addItem(item)
        
        total = self._historico.contar()
        exibidos = len(registros)

        # Gerencia Empty State
        if exibidos == 0:
            self._stack_lista.setCurrentWidget(self._widget_vazio)
            if termo_busca:
                self._lbl_msg_vazio.setText(f"Nenhum resultado para '{termo_busca}'")
            else:
                self._lbl_msg_vazio.setText("Nenhuma transcrição encontrada.\nSegure CapsLock para gravar.")
        else:
            self._stack_lista.setCurrentWidget(self._lista)

        self._lbl_contador.setText(
            f"{exibidos} de {total} transcrições" if termo_busca 
            else f"{total} transcrições"
        )
        
        logger.debug(f"Lista carregada: {exibidos} itens")
    
    def _on_busca_alterada(self, texto: str) -> None:
        """Handler para mudança no campo de busca."""
        self.atualizar_lista(texto.strip())
    
    def _on_item_selecionado(self, item: QListWidgetItem, anterior: QListWidgetItem) -> None:
        """Handler para seleção de item na lista."""
        if item is None:
            self._registro_selecionado = None
            self._txt_polido.clear()
            self._txt_bruto.clear()
            self._btn_copiar.setEnabled(False)
            self._btn_excluir.setEnabled(False)
            self._lbl_detalhes.setText("Selecione uma transcrição para ver detalhes")
            return
        
        registro_id = item.data(Qt.UserRole)
        self._registro_selecionado = self._historico.obter(registro_id)
        
        if self._registro_selecionado:
            reg = self._registro_selecionado
            self._lbl_detalhes.setText(
                f"📅 {reg.timestamp_formatado} | "
                f"⏱️ Duração: {reg.duracao_segundos:.1f}s | "
                f"📝 {len(reg.texto_polido)} caracteres"
            )
            self._txt_polido.setPlainText(reg.texto_polido)
            self._txt_bruto.setPlainText(reg.texto_bruto)
            self._btn_copiar.setEnabled(True)
            self._btn_excluir.setEnabled(True)
    
    def _on_copiar_clicado(self) -> None:
        """Handler para botão de copiar."""
        if self._registro_selecionado is None:
            return
        
        sucesso = copiar_para_clipboard(self._registro_selecionado.texto_polido)
        
        if sucesso:
            self._btn_copiar.setText("✅ Copiado!")
            logger.info(f"Texto do registro {self._registro_selecionado.id} copiado para clipboard")
            
            # Restaura texto do botão após 2 segundos
            from PySide6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self._btn_copiar.setText("📋 Copiar para Clipboard"))
        else:
            QMessageBox.warning(
                self,
                "Erro",
                "Não foi possível copiar para o clipboard."
            )

    def _on_excluir_clicado(self) -> None:
        """Handler para botão excluir."""
        if self._registro_selecionado is None:
            return
            
        resposta = QMessageBox.question(
            self,
            "Confirmar Exclusão",
            "Tem certeza que deseja excluir esta transcrição?\nEssa ação não pode ser desfeita.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if resposta == QMessageBox.Yes:
            if self._historico.excluir_por_id(self._registro_selecionado.id):
                self.atualizar_lista(self._txt_busca.text())
                QMessageBox.information(self, "Sucesso", "Transcrição excluída.")
            else:
                QMessageBox.critical(self, "Erro", "Falha ao excluir transcrição.")
    
    def _on_limpar_tudo_clicado(self) -> None:
        """Handler para botão limpar tudo."""
        total = self._historico.contar()
        if total == 0:
            QMessageBox.information(self, "Histórico Vazio", "Não há nada para excluir.")
            return

        resposta = QMessageBox.warning(
            self,
            "ATENÇÃO: Limpar Histórico",
            f"Você está prestes a excluir TODAS as {total} transcrições.\n\n"
            "ISSO É IRREVERSÍVEL!\n\n"
            "Tem certeza absoluta?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if resposta == QMessageBox.Yes:
            removidos = self._historico.excluir_tudo()
            self.atualizar_lista()
            QMessageBox.information(self, "Limpeza Concluída", f"{removidos} transcrições foram removidas.")
