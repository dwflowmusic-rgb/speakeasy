# -*- coding: utf-8 -*-
"""
VoiceFlow Transcriber - Entry Point Principal.

Aplicação desktop Windows para transcrição de voz com polimento via IA.
Consome no máximo 20MB de RAM em estado idle.

Uso:
    python voiceflow.py

Hotkey:
    CapsLock - Segure por 500ms para gravar, solte para processar
"""

import json
import os
import sys
import logging
import threading
from typing import Optional

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QObject, Signal, Slot, Qt, QMetaObject, Q_ARG

from core.logger import configurar_logging, obter_logger
from core.maquina_estados import MaquinaEstados, Estado
from core.historico import GerenciadorHistorico
from core.gerenciador_clipboard import (
    registrar_callback_notificacao,
    copiar_para_clipboard
)
from core.detector_tecla import DetectorCapsLock
from core.input_hook import KeyboardHook
from ui.icone_bandeja import IconeBandeja
from ui.janela_historico import JanelaHistorico
from ui.janela_retry import JanelaRetry
from ui.janela_configuracoes import JanelaConfiguracoes
from ui.status_widget import StatusWidget, StatusType
import core.autostart as autostart


# Configuração
ARQUIVO_CONFIG = os.path.join(os.path.dirname(__file__), 'config.json')
THRESHOLD_HOLD_MS_PADRAO = 500


class ClipboardWorker(QObject):
    """
    Worker para operações de clipboard na thread principal.
    
    Usa signal com BlockingQueuedConnection para garantir que
    a thread chamadora aguarde até a operação completar.
    """
    # Signal interno para executar cópia
    _copiar_signal = Signal(str)
    _resultado_signal = Signal(bool)
    
    def __init__(self):
        super().__init__()
        self._logger = obter_logger('clipboard_worker')
        self._resultado: bool = False
        self._evento_completo = threading.Event()
        
        # Conecta signal ao slot - executa na thread principal
        self._copiar_signal.connect(self._executar_copia, Qt.QueuedConnection)
        
        self._logger.info("ClipboardWorker inicializado")
    
    @Slot(str)
    def _executar_copia(self, texto: str) -> None:
        """Slot executado na thread principal do Qt."""
        self._logger.info(f"Executando cópia de {len(texto)} caracteres na thread principal")
        self._resultado = copiar_para_clipboard(texto)
        self._evento_completo.set()
    
    def copiar_bloqueante(self, texto: str, timeout_ms: int = 2000) -> bool:
        """
        Copia texto para clipboard de forma bloqueante.
        
        Emite signal para thread principal e AGUARDA até a operação
        completar antes de retornar. Isso garante que a thread
        secundária não finalize antes do clipboard ser atualizado.
        
        Args:
            texto: Texto a ser copiado
            timeout_ms: Timeout máximo em ms (padrão: 2000)
            
        Returns:
            True se cópia foi bem-sucedida
        """
        self._evento_completo.clear()
        self._resultado = False
        
        self._logger.info(f"Solicitando cópia bloqueante de {len(texto)} caracteres")
        self._copiar_signal.emit(texto)
        
        # Aguarda slot completar na thread principal
        sucesso = self._evento_completo.wait(timeout=timeout_ms / 1000.0)
        
        if not sucesso:
            self._logger.error(f"Timeout de {timeout_ms}ms aguardando clipboard")
            return False
        
        self._logger.info(f"Cópia bloqueante concluída - resultado: {self._resultado}")
        return self._resultado


class SignalBridge(QObject):
    """
    Ponte para sinais que precisam cruzar threads (Worker -> Main).
    """
    nova_transcricao = Signal()
    mudanca_estado = Signal(str)  # Passa nome do estado para thread principal


def carregar_configuracao() -> dict:
    """
    Carrega configurações do arquivo JSON.
    
    Returns:
        Dicionário com configurações
        
    Raises:
        SystemExit: Se arquivo não existir ou estiver malformado
    """
    logger = obter_logger('main')
    
    if not os.path.exists(ARQUIVO_CONFIG):
        logger.error(f"Arquivo de configuração não encontrado: {ARQUIVO_CONFIG}")
        print(f"\n[X] ERRO: Arquivo config.json não encontrado!")
        print(f"   Crie o arquivo em: {ARQUIVO_CONFIG}")
        print(f"   Com suas API keys do Groq e Gemini.")
        sys.exit(1)
    
    try:
        with open(ARQUIVO_CONFIG, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Valida campos obrigatórios
        if not config.get('transcription', {}).get('api_key'):
            logger.error("API key do Groq não configurada")
            print("\n[X] ERRO: API key do Groq não configurada em config.json")
            sys.exit(1)
        
        if not config.get('polishing', {}).get('api_key'):
            logger.error("API key do Gemini não configurada")
            print("\n[X] ERRO: API key do Gemini não configurada em config.json")
            sys.exit(1)
        
        logger.info("Configurações carregadas com sucesso")
        return config
        
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao parsear config.json: {e}")
        print(f"\n[X] ERRO: config.json está malformado!")
        print(f"   Detalhe: {e}")
        sys.exit(1)


class VoiceFlowApp:
    """
    Aplicação principal do VoiceFlow Transcriber.
    
    Coordena:
    - Interface Qt (system tray)
    - Detector de CapsLock (Hook de baixo nível ou Polling Win32)
    - Máquina de estados (processamento)
    - Clipboard síncrono bloqueante
    """
    
    def __init__(self):
        """Inicializa aplicação."""
        self._logger = obter_logger('main')
        
        # Carrega configurações
        self._config = carregar_configuracao()
        
        # Inicializa Qt (Deve ser o primeiro objeto Qt a ser criado)
        self._app = QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(False)
        
        # Ponte de sinais (Cross-thread communication)
        self._signals = SignalBridge()
        self._signals.nova_transcricao.connect(self._atualizar_historico_safe)
        self._signals.mudanca_estado.connect(self._atualizar_estado_safe)
        
        # Worker para clipboard síncrono bloqueante
        self._clipboard_worker = ClipboardWorker()
        
        # Inicializa máquina de estados
        self._maquina = MaquinaEstados(self._config)
        
        # Inicializa UI
        self._bandeja = IconeBandeja(self._app)

        # Verifica estado do autostart
        is_autostart = autostart.verificar_autostart()
        self._bandeja.definir_estado_autostart(is_autostart)
        
        # Configura callbacks
        self._bandeja.registrar_callback_sair(self._encerrar)
        self._bandeja.registrar_callback_historico(self._abrir_historico)
        self._bandeja.registrar_callback_configuracoes(self._abrir_configuracoes)
        self._bandeja.registrar_callback_retry(self._abrir_janela_retry)
        self._bandeja.registrar_callback_autostart(self._toggle_autostart)
        self._bandeja.registrar_callback_auto_enter(self._toggle_auto_enter)
        self._maquina.registrar_callback_estado(self._on_mudanca_estado)
        registrar_callback_notificacao(self._exibir_notificacao_qt)
        
        # Define estado inicial do Auto-Enter (lê do config)
        is_auto_enter = self._config.get('auto_enter', False)
        self._bandeja.definir_estado_auto_enter(is_auto_enter)
        
        # Janela de histórico (única instância, reutilizada)
        self._janela_historico: Optional[JanelaHistorico] = None
        self._janela_retry: Optional[JanelaRetry] = None
        self._janela_configuracoes: Optional[JanelaConfiguracoes] = None
        
        # Widget de status flutuante (OSD)
        self._status_widget = StatusWidget()
        # Widget começa oculto - só aparece durante gravação
        
        # Timer para verificar ESC durante gravação/processamento
        self._timer_esc = QTimer()
        self._timer_esc.timeout.connect(self._verificar_esc)
        self._timer_esc.start(50)  # Verifica a cada 50ms
        
        # Registra callback de clipboard síncrono bloqueante
        self._maquina.registrar_callback_clipboard(
            self._clipboard_worker.copiar_bloqueante
        )
        
        # Registra callback de nova transcrição (Auto-Refresh Histórico - Fase 4)
        self._maquina.registrar_callback_nova_transcricao(
            self._on_nova_transcricao
        )
        
        # Obtém threshold de configuração ou usa padrão
        threshold_ms = self._config.get('hotkey', {}).get(
            'threshold_ms', 
            THRESHOLD_HOLD_MS_PADRAO
        )
        
        # Tipo de detector: 'polling' (padrão, estável) ou 'hook' (experimental)
        tipo_detector = self._config.get('hotkey', {}).get('detector', 'polling')
        
        if tipo_detector == 'hook':
            # Novo detector via Low-Level Keyboard Hook
            # Permite suprimir toggle do CapsLock durante gravação
            self._logger.info("Usando detector de CapsLock via Low-Level Hook")
            self._detector = KeyboardHook(
                callback_iniciar=self._maquina.iniciar_gravacao,
                callback_parar=self._maquina.parar_gravacao,
                threshold_ms=threshold_ms
            )
        else:
            # Detector legado via Polling (fallback)
            self._logger.info("Usando detector de CapsLock via Polling (legado)")
            self._detector = DetectorCapsLock(
                callback_iniciar_gravacao=self._maquina.iniciar_gravacao,
                callback_parar_gravacao=self._maquina.parar_gravacao,
                threshold_ms=threshold_ms
            )
        
        self._logger.info(
            f"VoiceFlow Transcriber iniciado - "
            f"CapsLock hold {threshold_ms}ms para gravar (detector: {tipo_detector})"
        )
    
    def _exibir_notificacao_qt(self, titulo: str, mensagem: str) -> None:
        """Exibe notificação via QSystemTrayIcon."""
        self._bandeja.exibir_mensagem(titulo, mensagem)
    
    def _on_mudanca_estado(self, estado: Estado) -> None:
        """
        Handler para mudança de estado da máquina.
        Chamado pode vir de thread secundária, então apenas emite sinal.
        """
        self._signals.mudanca_estado.emit(estado.name)
        
    @Slot(str)
    def _atualizar_estado_safe(self, estado_nome: str) -> None:
        """
        Atualiza UI com novo estado na thread principal.
        """
        try:
            estado = Estado[estado_nome]
        except KeyError:
            return
            
        # Atualiza tooltip da bandeja
        tooltips = {
            Estado.IDLE: "VoiceFlow - Segure CapsLock por 500ms para gravar",
            Estado.RECORDING: "🔴 Gravando...",
            Estado.TRANSCRIBING: "⏳ Transcrevendo...",
            Estado.POLISHING: "✨ Polindo texto...",
            Estado.COMPLETE: "✅ Pronto!",
            Estado.ERROR: "❌ Erro no processamento"
        }
        self._bandeja.atualizar_tooltip(tooltips.get(estado, "VoiceFlow Transcriber"))
        
        # Atualiza widget de status (OSD)
        mapa_status = {
            Estado.IDLE: StatusType.IDLE,
            Estado.RECORDING: StatusType.RECORDING,
            Estado.TRANSCRIBING: StatusType.PROCESSING,
            Estado.POLISHING: StatusType.PROCESSING,
            Estado.COMPLETE: StatusType.SUCCESS,
            Estado.ERROR: StatusType.ERROR
        }
        status_widget = mapa_status.get(estado, StatusType.IDLE)
        self._status_widget.definir_status(status_widget)
    
    def _verificar_esc(self) -> None:
        """
        Verifica se ESC foi pressionado durante gravação/processamento.
        
        Se ESC for detectado em qualquer estado não-IDLE, cancela a operação
        ANTES de enviar para API (economia de tokens).
        """
        import ctypes
        VK_ESCAPE = 0x1B
        
        # Só verifica se não está em IDLE
        if self._maquina.estado == Estado.IDLE:
            return
        
        # GetAsyncKeyState retorna short: bit mais significativo = pressionada agora
        estado_esc = ctypes.windll.user32.GetAsyncKeyState(VK_ESCAPE)
        
        if estado_esc & 0x8000:
            self._logger.info("🔴 ESC detectado - cancelando operação!")
            
            # Cancela na FSM (seta flag antes de chamar API)
            self._maquina.cancelar()
            
            # Atualiza widget para mostrar cancelamento
            self._status_widget.definir_status(StatusType.CANCELLED)
    
    def _encerrar(self) -> None:
        """Encerra aplicação de forma limpa."""
        self._logger.info("Encerrando VoiceFlow Transcriber...")
        self._detector.parar()
    
    def _abrir_historico(self) -> None:
        """Abre janela de histórico."""
        self._logger.info("Abrindo janela de histórico")
        if not self._janela_historico:
            self._janela_historico = JanelaHistorico(self._maquina._historico)
        
        self._janela_historico.atualizar_lista()
        self._janela_historico.show()
        self._janela_historico.raise_()
        self._janela_historico.activateWindow()

    def _abrir_janela_retry(self) -> None:
        """Abre janela de recuperação de falhas."""
        self._logger.info("Abrindo janela de retry")
        if not self._janela_retry:
            self._janela_retry = JanelaRetry(self._maquina)
        
        self._janela_retry.atualizar_lista()
        self._janela_retry.show()
        self._janela_retry.raise_()
        self._janela_retry.activateWindow()

    def _abrir_configuracoes(self) -> None:
        """Abre janela de configurações."""
        self._logger.info("Abrindo janela de configurações")
        # Cria nova instância para garantir estado fresco
        self._janela_configuracoes = JanelaConfiguracoes(self._config)
        self._janela_configuracoes.configuracao_salva.connect(self._on_configuracao_salva)

        self._janela_configuracoes.show()
        self._janela_configuracoes.raise_()
        self._janela_configuracoes.activateWindow()

    @Slot(dict)
    def _on_configuracao_salva(self, novo_config: dict) -> None:
        """Callback para quando configurações são salvas."""
        self._logger.info("Aplicando novas configurações...")

        # Atualiza configuração principal
        self._config.update(novo_config)

        # Propaga para máquina de estados (e clientes API)
        self._maquina.atualizar_configuracao(self._config)

        # Atualiza UI (Tray Icon)
        self._bandeja.definir_estado_auto_enter(self._config.get('auto_enter', False))

        self._exibir_notificacao_qt("Configurações", "Configurações atualizadas com sucesso!")

    def _toggle_autostart(self, ativar: bool) -> None:
        """Alterna inicialização automática."""
        if autostart.definir_autostart(ativar):
            msg = "ativada" if ativar else "desativada"
            self._exibir_notificacao_qt("Inicialização Automática", f"Iniciação com Windows {msg}.")
        else:
            # Reverte checkbox em caso de falha
            self._bandeja.definir_estado_autostart(not ativar)
            self._exibir_notificacao_qt("Erro", "Falha ao alterar configuração de registro.")

    def _toggle_auto_enter(self, ativar: bool) -> None:
        """Alterna Auto-Enter (pressiona Enter após colar)."""
        self._config['auto_enter'] = ativar
        
        # Salva no config.json
        try:
            with open(ARQUIVO_CONFIG, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            
            msg = "ativado" if ativar else "desativado"
            self._exibir_notificacao_qt("Auto-Enter", f"Enter automático após colar {msg}.")
            self._logger.info(f"Auto-Enter {msg} e salvo em config.json")
        except Exception as e:
            self._logger.error(f"Erro ao salvar config: {e}")
            # Reverte checkbox em caso de falha
            self._bandeja.definir_estado_auto_enter(not ativar)
            self._config['auto_enter'] = not ativar
            self._exibir_notificacao_qt("Erro", "Falha ao salvar configuração.")
        
    
    def _on_nova_transcricao(self) -> None:
        """
        Callback chamado pela FSM (Thread Secundária).
        Emite sinal para atualizar GUI na Thread Principal.
        """
        self._signals.nova_transcricao.emit()
        
    @Slot()
    def _atualizar_historico_safe(self) -> None:
        """
        Slot executado na Thread Principal.
        Atualiza a janela de histórico com segurança.
        """
        if self._janela_historico and self._janela_historico.isVisible():
            self._logger.info("Auto-refresh: Atualizando lista de histórico (Thread Principal)")
            self._janela_historico.atualizar_lista()
    
    def executar(self) -> int:
        """Executa loop principal da aplicação."""
        self._logger.info("Entrando no loop principal")
        
        # Inicia detector de CapsLock
        self._detector.iniciar()
        
        # Realiza manutenção do histórico (Retenção de 5 dias)
        try:
            dias_retencao = self._config.get('history', {}).get('retention_days', 5)
            removidos = GerenciadorHistorico().limpar_antigos(dias_retencao)
            if removidos > 0:
                print(f"   🧹 Manutenção: {removidos} registros antigos removidos do histórico.")
        except Exception as e:
            self._logger.error(f"Erro na manutenção do histórico: {e}")
        
        print(f"\n✅ VoiceFlow Transcriber iniciado!")
        print(f"   Hotkey: CapsLock (segure por 500ms para gravar)")
        print(f"   Ícone disponível na bandeja do sistema.")
        print(f"\n   Pressione Ctrl+C no terminal para encerrar.\n")
        
        return self._app.exec()


def main():
    """Ponto de entrada principal."""
    # Inicializa logging
    configurar_logging(nivel=logging.INFO)
    logger = obter_logger('main')
    
    logger.info("=" * 60)
    logger.info("VoiceFlow Transcriber - Iniciando")
    logger.info("=" * 60)
    
    try:
        app = VoiceFlowApp()
        codigo_saida = app.executar()
        
    except KeyboardInterrupt:
        logger.info("Interrupção por teclado (Ctrl+C)")
        codigo_saida = 0
        
    except Exception as e:
        logger.critical(f"Erro fatal: {e}", exc_info=True)
        print(f"\n[X] Erro fatal: {e}")
        codigo_saida = 1
    
    logger.info(f"VoiceFlow Transcriber encerrado (código: {codigo_saida})")
    sys.exit(codigo_saida)


if __name__ == '__main__':
    main()
