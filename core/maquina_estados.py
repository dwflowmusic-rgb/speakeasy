# -*- coding: utf-8 -*-
"""
Máquina de Estados do VoiceFlow Transcriber.

Gerencia transições entre estados: IDLE → RECORDING → TRANSCRIBING → POLISHING → COMPLETE.
Cada transição é logada para diagnóstico.
"""

from enum import Enum, auto
from typing import Optional, Callable
import threading

from PySide6.QtCore import QTimer, QCoreApplication

from core.logger import obter_logger
from core.captura_audio import CapturadorAudio, limpar_arquivo_temporario
from core.cliente_api import ClienteAPI
from core.gerenciador_clipboard import (
    copiar_para_clipboard,
    notificar_sucesso,
    notificar_erro
)
from core.historico import GerenciadorHistorico
from core.detector_foco import obter_janela_ativa, simular_ctrl_v, simular_enter
import time
import os
import shutil
import json
from datetime import datetime

DIR_FALHAS = os.path.join("data", "failed_audios")

logger = obter_logger('maquina_estados')


class Estado(Enum):
    """Estados possíveis da máquina de estados."""
    IDLE = auto()           # Aguardando hotkey
    RECORDING = auto()      # Capturando áudio
    TRANSCRIBING = auto()   # Enviando para Groq
    POLISHING = auto()      # Enviando para Gemini
    COMPLETE = auto()       # Processamento concluído
    ERROR = auto()          # Erro no processamento


class MaquinaEstados:
    """
    Máquina de estados finitos para controle do fluxo de transcrição.
    
    Transições:
        IDLE → RECORDING (hotkey pressionado)
        RECORDING → TRANSCRIBING (hotkey solto)
        TRANSCRIBING → POLISHING (transcrição OK)
        TRANSCRIBING → ERROR (falha API)
        POLISHING → COMPLETE (texto polido ou fallback)
        COMPLETE → IDLE (após clipboard + notificação)
        ERROR → IDLE (após notificação de erro)
    """
    
    def __init__(self, config: dict):
        """
        Inicializa máquina de estados.
        
        Args:
            config: Configurações da aplicação
        """
        self._estado: Estado = Estado.IDLE
        self._config = config
        
        # Componentes
        self._capturador = CapturadorAudio()
        self._cliente_api = ClienteAPI(config)
        self._cliente_api = ClienteAPI(config)
        self._historico = GerenciadorHistorico()
        
        # Controle de foco (Fase 3)
        self._janela_inicio: int = 0
        
        # Dados da transcrição atual
        self._caminho_audio: Optional[str] = None
        self._duracao_audio: float = 0.0
        self._texto_bruto: Optional[str] = None
        self._texto_polido: Optional[str] = None
        
        # Callbacks para operações que devem rodar na thread principal
        self._callback_estado: Optional[Callable[[Estado], None]] = None
        self._callback_clipboard: Optional[Callable[[str], None]] = None
        self._callback_nova_transcricao: Optional[Callable[[], None]] = None
        
        # Flag de cancelamento (Fase 4)
        self._cancelado = False
        
        logger.info("Máquina de estados inicializada - Estado: IDLE")
    
    @property
    def estado(self) -> Estado:
        """Retorna estado atual."""
        return self._estado
    
    @property
    def esta_gravando(self) -> bool:
        """Retorna True se está gravando áudio."""
        return self._estado == Estado.RECORDING
    
    @property
    def duracao_gravacao(self) -> float:
        """Retorna duração da gravação atual em segundos."""
        return self._capturador.duracao_atual
    
    def registrar_callback_estado(self, callback: Callable[[Estado], None]) -> None:
        """
        Registra callback para notificação de mudança de estado.
        
        Args:
            callback: Função chamada com novo estado
        """
        self._callback_estado = callback
    
    def registrar_callback_clipboard(self, callback: Callable[[str], None]) -> None:
        """
        Registra callback para copiar texto para clipboard na thread principal.
        
        IMPORTANTE: Este callback DEVE ser executado na thread principal do Qt
        para evitar erros COM no Windows.
        
        Args:
            callback: Função que recebe texto e copia para clipboard
        """
        self._callback_clipboard = callback
        logger.info("Callback de clipboard registrado")
    
    def registrar_callback_nova_transcricao(self, callback: Callable[[], None]) -> None:
        """
        Registra callback notificar quando uma nova transcrição é salva.
        Útil para atualizar janelas de histórico automaticamente.
        """
        self._callback_nova_transcricao = callback
    
    def _transitar(self, novo_estado: Estado) -> None:
        """
        Executa transição de estado com logging.
        
        Args:
            novo_estado: Estado destino
        """
        estado_anterior = self._estado
        self._estado = novo_estado
        logger.info(f"Transição: {estado_anterior.name} → {novo_estado.name}")
        
        if self._callback_estado:
            try:
                self._callback_estado(novo_estado)
            except Exception as e:
                logger.warning(f"Erro no callback de estado: {e}")
    
    def iniciar_gravacao(self) -> bool:
        """
        Inicia gravação de áudio (IDLE → RECORDING).
        
        Returns:
            True se transição foi bem-sucedida
        """
        if self._estado != Estado.IDLE:
            logger.warning(f"Tentativa de iniciar gravação em estado inválido: {self._estado.name}")
            return False
        
        # Limpa dados anteriores
        self._caminho_audio = None
        self._duracao_audio = 0.0
        self._texto_bruto = None
        self._texto_bruto = None
        self._texto_polido = None
        
        # Captura janela ativa para colagem inteligente
        self._janela_inicio = obter_janela_ativa()
        logger.debug(f"Janela ativa no início: {self._janela_inicio}")
        
        # Tenta iniciar captura
        if self._capturador.iniciar_gravacao():
            self._transitar(Estado.RECORDING)
            return True
        else:
            notificar_erro("Microfone não disponível")
            return False
    
    def cancelar(self) -> None:
        """
        Cancela a operação atual.
        
        Se estiver gravando: para gravação e descarta áudio.
        Se estiver processando: seta flag para abortar ANTES de chamar API.
        
        Isso evita gasto de tokens ao cancelar rapidamente.
        """
        if self._estado == Estado.IDLE:
            logger.debug("Cancelamento ignorado - já em IDLE")
            return
        
        logger.info(f"🚫 Cancelamento solicitado em estado: {self._estado.name}")
        
        # Seta flag para abortar processamento
        self._cancelado = True
        
        # Se estiver gravando, para a gravação
        if self._estado == Estado.RECORDING:
            self._capturador.parar_gravacao()  # Descarta áudio
            
        # Limpa arquivo temporário se existir
        if self._caminho_audio:
            limpar_arquivo_temporario(self._caminho_audio)
            self._caminho_audio = None
        
        # Transita para IDLE
        self._transitar(Estado.IDLE)
        logger.info("✅ Operação cancelada - nenhum token consumido")
    
    def parar_gravacao(self) -> None:
        """
        Para gravação e inicia processamento (RECORDING → TRANSCRIBING).
        Processamento acontece em thread separada para não bloquear UI.
        """
        if self._estado != Estado.RECORDING:
            logger.warning(f"Tentativa de parar gravação em estado inválido: {self._estado.name}")
            return
        
        # Para captura e salva arquivo
        caminho, duracao = self._capturador.parar_gravacao()
        
        if caminho is None:
            # Gravação muito curta - volta para IDLE silenciosamente
            self._transitar(Estado.IDLE)
            return
        
        self._caminho_audio = caminho
        self._duracao_audio = duracao
        
        # Inicia processamento em thread separada
        self._transitar(Estado.TRANSCRIBING)
        thread = threading.Thread(target=self._processar_audio, daemon=True)
        thread.start()
    
    def _processar_audio(self) -> None:
        """
        Processa áudio: transcrição + polimento.
        Executado em thread separada.
        """
        try:
            # Verifica cancelamento ANTES de chamar API (economia de tokens)
            if self._cancelado:
                logger.info("🚫 Processamento abortado por cancelamento")
                self._cancelado = False  # Reset flag
                self._finalizar()
                return
            
            # TRANSCRIBING: Envia para Groq
            texto, erro = self._cliente_api.transcrever(self._caminho_audio)
            
            # Verifica cancelamento após transcrição (antes de polimento)
            if self._cancelado:
                logger.info("🚫 Transcrição concluída mas polimento abortado por cancelamento")
                self._cancelado = False
                self._finalizar()
                return
            
            if texto is None:
                logger.error(f"Transcrição falhou: {erro}")
                self._salvar_audio_falha(erro or "Falha na transcrição")
                self._transitar(Estado.ERROR)
                notificar_erro(erro or "Falha na transcrição")
                self._finalizar()
                return
            
            self._texto_bruto = texto
            
            # POLISHING: Envia para Gemini
            self._transitar(Estado.POLISHING)
            texto_polido, foi_polido = self._cliente_api.polir(texto)
            self._texto_polido = texto_polido
            
            if not foi_polido:
                logger.warning("Usando texto bruto (polimento falhou)")
            
            # PERSISTÊNCIA-PRIMEIRO (Write-Ahead Logging)
            # Salva no histórico ANTES de qualquer operação de clipboard
            # Se SQLite falhar, tenta salvar em arquivo de emergência
            persistencia_sucesso = False
            try:
                registro_id = self._historico.salvar(
                    texto_bruto=self._texto_bruto,
                    texto_polido=self._texto_polido,
                    duracao_segundos=self._duracao_audio
                )
                logger.info(f"✅ Transcrição persistida no histórico: ID {registro_id}")
                persistencia_sucesso = True
                
                # Notifica que há nova transcrição (para refresh do histórico)
                if self._callback_nova_transcricao:
                    try:
                        self._callback_nova_transcricao()
                    except Exception as e:
                        logger.error(f"Erro no callback de nova transcrição: {e}")
                        
            except Exception as e:
                logger.error(f"CRÍTICO: Falha ao salvar no histórico SQLite: {e}")
                # FAIL-SAFE: Tentar salvar em arquivo de emergência no Desktop
                try:
                    import os
                    from datetime import datetime
                    desktop = os.path.join(os.environ.get('USERPROFILE', '~'), 'Desktop')
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    arquivo_emergencia = os.path.join(desktop, f"VoiceFlow_EMERGENCIA_{timestamp}.txt")
                    with open(arquivo_emergencia, 'w', encoding='utf-8') as f:
                        f.write(f"=== TRANSCRIÇÃO DE EMERGÊNCIA ===\n")
                        f.write(f"Data/Hora: {datetime.now().isoformat()}\n")
                        f.write(f"Duração: {self._duracao_audio:.1f}s\n\n")
                        f.write(f"--- TEXTO BRUTO ---\n{self._texto_bruto}\n\n")
                        f.write(f"--- TEXTO POLIDO ---\n{self._texto_polido}\n")
                    logger.warning(f"⚠️ Transcrição salva em arquivo de emergência: {arquivo_emergencia}")
                    notificar_erro(f"Erro no banco de dados! Texto salvo em: {arquivo_emergencia}")
                    persistencia_sucesso = True  # Conseguimos salvar de alguma forma
                except Exception as e2:
                    logger.critical(f"FALHA TOTAL: Não conseguiu salvar nem no SQLite nem em arquivo: {e2}")
                    notificar_erro("CRÍTICO: Impossível salvar transcrição!")
                    # Ainda assim, tentar entregar ao clipboard como última chance
            
            # COMPLETE: Copia para clipboard via callback bloqueante
            self._transitar(Estado.COMPLETE)
            
            if self._callback_clipboard:
                # Callback é bloqueante - aguarda até clipboard ser atualizado
                logger.info(f"Copiando {len(self._texto_polido)} caracteres para clipboard")
                sucesso = self._callback_clipboard(self._texto_polido)
                
                if sucesso:
                    logger.info("Clipboard atualizado com sucesso")
                else:
                    logger.warning("Falha ao atualizar clipboard")
            else:
                # Fallback: tenta diretamente (pode falhar no Windows)
                logger.warning("Callback de clipboard não registrado - tentando diretamente")
                copiar_para_clipboard(self._texto_polido)
            
            # COLAGEM INTELIGENTE (Fase 3)
            # Verifica se usuário manteve foco na mesma janela
            janela_atual = obter_janela_ativa()
            
            if janela_atual == self._janela_inicio and self._janela_inicio != 0:
                logger.info("Foco preservado - Colando automaticamente")
                if simular_ctrl_v():
                    notificar_sucesso("Transcrição colada com sucesso!")
                    
                    # AUTO-ENTER: Se habilitado, aguarda 800ms e pressiona Enter
                    if self._config.get('auto_enter', False):
                        def _do_enter():
                            if simular_enter():
                                logger.info("Auto-Enter executado com sucesso")
                            else:
                                logger.warning("Falha ao executar Auto-Enter")

                        # Tenta usar timer do Qt se disponível
                        app = QCoreApplication.instance()
                        if app:
                            QTimer.singleShot(800, app, _do_enter)
                        else:
                            # Fallback para testes sem loop Qt ou execução standalone
                            time.sleep(0.8)
                            _do_enter()
                else:
                    notificar_sucesso("Transcrição no clipboard (falha ao colar)")
            else:
                logger.info(f"Foco mudou ou inválido ({self._janela_inicio} -> {janela_atual}) - Mantendo no clipboard")
                notificar_sucesso("Transcrição pronta no clipboard (foco alterado)")
            

            
        except Exception as e:
            logger.error(f"Erro no processamento: {e}", exc_info=True)
            self._salvar_audio_falha(f"Erro de processamento: {str(e)}")
            self._transitar(Estado.ERROR)
            notificar_erro("Erro inesperado no processamento")
        
        finally:
            self._finalizar()

    def _salvar_audio_falha(self, erro_msg: str) -> None:
        """Salva áudio falho para retry posterior."""
        if not self._caminho_audio or not os.path.exists(self._caminho_audio):
            return

        try:
            if not os.path.exists(DIR_FALHAS):
                os.makedirs(DIR_FALHAS)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_base = f"falha_{timestamp}"
            caminho_destino = os.path.join(DIR_FALHAS, f"{nome_base}.wav")
            caminho_json = os.path.join(DIR_FALHAS, f"{nome_base}.json")

            # Copia arquivo (preserva original para _finalizar limpar se for temp)
            shutil.copy2(self._caminho_audio, caminho_destino)

            # Salva metadados
            dados = {
                "timestamp": datetime.now().isoformat(),
                "erro": str(erro_msg),
                "arquivo_audio": caminho_destino,
                "duracao": self._duracao_audio
            }
            
            with open(caminho_json, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=4, ensure_ascii=False)
                
            logger.info(f"💾 Áudio falho salvo em: {caminho_destino}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar áudio falho: {e}")

    def reprocessar_arquivo(self, caminho_wav: str) -> None:
        """
        Inicia processamento de um arquivo existente (Retry).
        
        Args:
            caminho_wav: Caminho absoluto do arquivo WAV
        """
        if self._estado != Estado.IDLE:
             logger.warning("Falha ao reprocessar: Máquina não está em IDLE")
             notificar_erro("Aguarde o processamento atual terminar")
             return
             
        if not os.path.exists(caminho_wav):
            logger.error(f"Arquivo não encontrado para reprocessamento: {caminho_wav}")
            notificar_erro("Arquivo de áudio não encontrado")
            return
            
        logger.info(f"♻️ Iniciando reprocessamento de: {caminho_wav}")
        
        # Define estado
        self._caminho_audio = caminho_wav
        self._duracao_audio = 0.0 
        
        # Inicia processamento
        self._transitar(Estado.TRANSCRIBING)
        thread = threading.Thread(target=self._processar_audio, daemon=True)
        thread.start()
    
    def _finalizar(self) -> None:
        """Limpa recursos e retorna para IDLE."""
        # Remove arquivo temporário
        if self._caminho_audio:
            limpar_arquivo_temporario(self._caminho_audio)
            self._caminho_audio = None
        
        # Retorna para IDLE
        self._transitar(Estado.IDLE)
