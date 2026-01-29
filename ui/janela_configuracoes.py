# -*- coding: utf-8 -*-
"""
Janela de Configurações do VoiceFlow Transcriber.

Permite visualizar e editar configurações do sistema.
"""

import json
import os
from typing import Dict, Any

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QCheckBox, QSpinBox, QComboBox,
    QPushButton, QFormLayout, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, Signal

from core.logger import obter_logger

logger = obter_logger('janela_configuracoes')

# Caminho do arquivo de configuração
ARQUIVO_CONFIG = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')


class JanelaConfiguracoes(QDialog):
    """
    Janela para edição de configurações.
    Emite sinal quando configurações são salvas.
    """

    configuracao_salva = Signal(dict)

    def __init__(self, config_atual: Dict[str, Any], parent=None):
        super().__init__(parent)
        self._config = config_atual
        self._setup_ui()
        self._carregar_valores()

    def _setup_ui(self) -> None:
        """Configura interface gráfica."""
        self.setWindowTitle("VoiceFlow - Configurações")
        self.setMinimumSize(500, 400)
        self.setModal(True)

        layout_principal = QVBoxLayout(self)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.addTab(self._criar_tab_transcricao(), "📝 Transcrição")
        self._tabs.addTab(self._criar_tab_polimento(), "✨ Polimento")
        self._tabs.addTab(self._criar_tab_geral(), "⚙️ Geral")
        self._tabs.addTab(self._criar_tab_avancado(), "🛠️ Avançado")

        layout_principal.addWidget(self._tabs)

        # Botões
        layout_botoes = QHBoxLayout()
        layout_botoes.addStretch()

        self._btn_cancelar = QPushButton("Cancelar")
        self._btn_cancelar.clicked.connect(self.reject)

        self._btn_salvar = QPushButton("Salvar")
        self._btn_salvar.clicked.connect(self._salvar)
        self._btn_salvar.setDefault(True)

        layout_botoes.addWidget(self._btn_cancelar)
        layout_botoes.addWidget(self._btn_salvar)

        layout_principal.addLayout(layout_botoes)

    def _criar_tab_transcricao(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)

        self._txt_groq_key = QLineEdit()
        self._txt_groq_key.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        self._txt_groq_key.setPlaceholderText("gsk_...")

        self._txt_groq_model = QLineEdit()
        self._txt_groq_model.setPlaceholderText("ex: whisper-large-v3-turbo")

        layout.addRow("API Key (Groq):", self._txt_groq_key)
        layout.addRow("Modelo:", self._txt_groq_model)

        lbl_info = QLabel("Chaves API do Groq são gratuitas (beta).")
        lbl_info.setStyleSheet("color: gray; font-size: 11px;")
        layout.addRow("", lbl_info)

        return widget

    def _criar_tab_polimento(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)

        self._txt_gemini_key = QLineEdit()
        self._txt_gemini_key.setEchoMode(QLineEdit.PasswordEchoOnEdit)

        self._txt_gemini_model = QLineEdit()
        self._txt_gemini_model.setPlaceholderText("ex: gemini-1.5-flash")

        layout.addRow("API Key (Gemini):", self._txt_gemini_key)
        layout.addRow("Modelo:", self._txt_gemini_model)

        lbl_info = QLabel("Google AI Studio (Gemini) oferece tier gratuito.")
        lbl_info.setStyleSheet("color: gray; font-size: 11px;")
        layout.addRow("", lbl_info)

        return widget

    def _criar_tab_geral(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group_comportamento = QGroupBox("Comportamento")
        layout_comportamento = QVBoxLayout(group_comportamento)

        self._chk_auto_enter = QCheckBox("Pressionar Enter automaticamente após colar")
        self._chk_auto_enter.setToolTip("Envia a mensagem imediatamente após colar (útil para chat apps)")
        layout_comportamento.addWidget(self._chk_auto_enter)

        layout.addWidget(group_comportamento)

        group_historico = QGroupBox("Histórico")
        layout_historico = QFormLayout(group_historico)

        self._spin_retencao = QSpinBox()
        self._spin_retencao.setRange(1, 365)
        self._spin_retencao.setSuffix(" dias")

        layout_historico.addRow("Manter histórico por:", self._spin_retencao)
        layout.addWidget(group_historico)

        layout.addStretch()
        return widget

    def _criar_tab_avancado(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group_hotkey = QGroupBox("Hotkey (CapsLock)")
        layout_hotkey = QFormLayout(group_hotkey)

        self._spin_threshold = QSpinBox()
        self._spin_threshold.setRange(100, 5000)
        self._spin_threshold.setSingleStep(50)
        self._spin_threshold.setSuffix(" ms")
        self._spin_threshold.setToolTip("Tempo que CapsLock deve ser segurado para ativar gravação")

        self._combo_detector = QComboBox()
        self._combo_detector.addItems(["polling", "hook"])
        self._combo_detector.setToolTip("Hook é mais rápido mas pode ser instável em alguns sistemas")

        layout_hotkey.addRow("Tempo de ativação:", self._spin_threshold)
        layout_hotkey.addRow("Método de detecção:", self._combo_detector)

        layout.addWidget(group_hotkey)

        lbl_aviso = QLabel("⚠️ Alterações aqui requerem reinício do aplicativo.")
        lbl_aviso.setStyleSheet("color: #e67e22; font-weight: bold;")
        layout.addWidget(lbl_aviso)

        layout.addStretch()
        return widget

    def _carregar_valores(self) -> None:
        """Preenche widgets com valores da configuração."""
        try:
            # Transcrição
            t = self._config.get('transcription', {})
            self._txt_groq_key.setText(t.get('api_key', ''))
            self._txt_groq_model.setText(t.get('model', 'whisper-large-v3-turbo'))

            # Polimento
            p = self._config.get('polishing', {})
            self._txt_gemini_key.setText(p.get('api_key', ''))
            self._txt_gemini_model.setText(p.get('model', 'gemini-1.5-flash'))

            # Geral
            self._chk_auto_enter.setChecked(self._config.get('auto_enter', False))

            h = self._config.get('history', {})
            self._spin_retencao.setValue(h.get('retention_days', 5))

            # Avançado
            hk = self._config.get('hotkey', {})
            self._spin_threshold.setValue(hk.get('threshold_ms', 500))

            detector = hk.get('detector', 'polling')
            idx = self._combo_detector.findText(detector)
            if idx >= 0:
                self._combo_detector.setCurrentIndex(idx)

        except Exception as e:
            logger.error(f"Erro ao carregar valores na janela de configurações: {e}")
            QMessageBox.critical(self, "Erro", "Falha ao carregar configurações atuais.")

    def _salvar(self) -> None:
        """Valida, salva no arquivo e emite sinal."""
        # Validação básica
        if not self._txt_groq_key.text().strip():
            QMessageBox.warning(self, "Atenção", "API Key do Groq é obrigatória.")
            self._tabs.setCurrentIndex(0)
            self._txt_groq_key.setFocus()
            return

        if not self._txt_gemini_key.text().strip():
            QMessageBox.warning(self, "Atenção", "API Key do Gemini é obrigatória.")
            self._tabs.setCurrentIndex(1)
            self._txt_gemini_key.setFocus()
            return

        # Atualiza dicionário
        novo_config = self._config.copy()

        novo_config['transcription'] = {
            'api_key': self._txt_groq_key.text().strip(),
            'model': self._txt_groq_model.text().strip()
        }

        novo_config['polishing'] = {
            'api_key': self._txt_gemini_key.text().strip(),
            'model': self._txt_gemini_model.text().strip()
        }

        novo_config['auto_enter'] = self._chk_auto_enter.isChecked()

        novo_config['history'] = {
            'retention_days': self._spin_retencao.value()
        }

        # Preserva outros campos de hotkey se existirem
        hotkey_config = novo_config.get('hotkey', {}).copy()
        hotkey_config['threshold_ms'] = self._spin_threshold.value()
        hotkey_config['detector'] = self._combo_detector.currentText()
        novo_config['hotkey'] = hotkey_config

        # Salva em arquivo
        try:
            with open(ARQUIVO_CONFIG, 'w', encoding='utf-8') as f:
                json.dump(novo_config, f, indent=4, ensure_ascii=False)

            logger.info("Configurações salvas em config.json")
            self.configuracao_salva.emit(novo_config)
            self.accept()

        except Exception as e:
            logger.error(f"Erro ao salvar config.json: {e}")
            QMessageBox.critical(self, "Erro", f"Falha ao salvar arquivo de configuração:\n{e}")
