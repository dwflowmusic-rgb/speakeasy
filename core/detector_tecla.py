# -*- coding: utf-8 -*-
"""
Detector de Tecla CapsLock via Win32 API.

Usa GetAsyncKeyState para polling direto do estado da tecla,
bypassing bibliotecas de abstração que tratam CapsLock como toggle.

Integra com QTimer para verificação a cada 20ms na thread principal do Qt.
"""

import ctypes
from ctypes import wintypes
from typing import Optional, Callable
from enum import Enum, auto

from PySide6.QtCore import QTimer, QObject

from core.logger import obter_logger

logger = obter_logger('detector_tecla')

# Win32 API
user32 = ctypes.windll.user32

# Virtual Key Code para CapsLock
VK_CAPITAL = 0x14

# Constantes de configuração
INTERVALO_POLLING_IDLE_MS = 100  # 10Hz quando ocioso
INTERVALO_POLLING_ACTIVE_MS = 20  # 50Hz quando interagindo
THRESHOLD_HOLD_MS_PADRAO = 500  # 500ms para considerar "hold intencional"
THRESHOLD_HOLD_MS_MIN = 200
THRESHOLD_HOLD_MS_MAX = 1500
DURACAO_MAXIMA_GRAVACAO_MS = 5 * 60 * 1000  # 5 minutos


class EstadoDetector(Enum):
    """Estados do detector de tecla."""
    AGUARDANDO = auto()      # Esperando press inicial
    CONTANDO_HOLD = auto()   # Tecla pressionada, contando tempo
    GRAVANDO = auto()        # Threshold atingido, gravação ativa


class DetectorCapsLock(QObject):
    """
    Detector de CapsLock via polling Win32 API.
    
    Funciona verificando estado da tecla a cada 20ms via GetAsyncKeyState,
    sem depender de eventos que não funcionam bem com teclas toggle.
    
    Uso:
        detector = DetectorCapsLock(callback_iniciar, callback_parar)
        detector.iniciar()
    """
    
    def __init__(
        self,
        callback_iniciar_gravacao: Callable[[], bool],
        callback_parar_gravacao: Callable[[], None],
        threshold_ms: int = THRESHOLD_HOLD_MS_PADRAO
    ):
        """
        Inicializa detector.
        
        Args:
            callback_iniciar_gravacao: Chamado quando threshold é atingido
            callback_parar_gravacao: Chamado quando tecla é solta durante gravação
            threshold_ms: Tempo em ms para considerar hold intencional (padrão: 500)
        """
        super().__init__()
        
        self._callback_iniciar = callback_iniciar_gravacao
        self._callback_parar = callback_parar_gravacao
        
        # Valida e armazena threshold
        self._threshold_ms = max(
            THRESHOLD_HOLD_MS_MIN,
            min(THRESHOLD_HOLD_MS_MAX, threshold_ms)
        )
        
        # Estado interno
        self._estado = EstadoDetector.AGUARDANDO
        self._contador_hold_ms = 0
        self._contador_gravacao_ms = 0
        
        # Timer Qt para polling
        self._timer: Optional[QTimer] = None
        
        logger.info(
            f"DetectorCapsLock inicializado - threshold: {self._threshold_ms}ms, "
            f"polling idle: {INTERVALO_POLLING_IDLE_MS}ms"
        )
    
    @property
    def threshold_ms(self) -> int:
        """Retorna threshold atual em milissegundos."""
        return self._threshold_ms
    
    @threshold_ms.setter
    def threshold_ms(self, valor: int) -> None:
        """
        Define novo threshold.
        
        Args:
            valor: Novo threshold em ms (será clamped para range válido)
        """
        self._threshold_ms = max(
            THRESHOLD_HOLD_MS_MIN,
            min(THRESHOLD_HOLD_MS_MAX, valor)
        )
        logger.info(f"Threshold atualizado para {self._threshold_ms}ms")
    
    def iniciar(self) -> None:
        """Inicia monitoramento de CapsLock."""
        if self._timer is not None:
            logger.warning("Detector já está ativo")
            return
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._verificar_estado_tecla)
        self._timer.start(INTERVALO_POLLING_IDLE_MS)
        
        self._estado = EstadoDetector.AGUARDANDO
        self._contador_hold_ms = 0
        self._contador_gravacao_ms = 0
        
        logger.info("Monitoramento de CapsLock iniciado (polling Win32 API)")
    
    def parar(self) -> None:
        """Para monitoramento de CapsLock."""
        if self._timer is not None:
            self._timer.stop()
            self._timer.deleteLater()
            self._timer = None
        
        self._estado = EstadoDetector.AGUARDANDO
        logger.info("Monitoramento de CapsLock parado")
    
    def _tecla_pressionada(self) -> bool:
        """
        Verifica se CapsLock está fisicamente pressionada via Win32 API.
        
        Usa GetAsyncKeyState que retorna estado atual da tecla,
        não o estado toggle de caps lock on/off.
        
        Returns:
            True se tecla está fisicamente pressionada
        """
        # GetAsyncKeyState retorna short: bit mais significativo indica se pressionada
        estado = user32.GetAsyncKeyState(VK_CAPITAL)
        return bool(estado & 0x8000)
    
    def _verificar_estado_tecla(self) -> None:
        """
        Callback do timer - verifica estado da tecla.
        
        Implementa máquina de estados com polling dinâmico:
        - AGUARDANDO: espera press inicial (polling lento 100ms)
        - CONTANDO_HOLD: conta tempo de hold (polling rápido 20ms)
        - GRAVANDO: monitora release para parar (polling rápido 20ms)
        """
        tecla_pressionada = self._tecla_pressionada()
        intervalo_atual = self._timer.interval()
        
        if self._estado == EstadoDetector.AGUARDANDO:
            if tecla_pressionada:
                # Transição: AGUARDANDO → CONTANDO_HOLD
                self._estado = EstadoDetector.CONTANDO_HOLD
                self._contador_hold_ms = intervalo_atual

                # Aumenta frequência de polling para precisão durante interação
                self._timer.setInterval(INTERVALO_POLLING_ACTIVE_MS)

                logger.debug(f"CapsLock pressionada - iniciando contagem de hold (polling acelerado)")
        
        elif self._estado == EstadoDetector.CONTANDO_HOLD:
            if tecla_pressionada:
                # Continua contando
                self._contador_hold_ms += intervalo_atual
                
                if self._contador_hold_ms >= self._threshold_ms:
                    # Threshold atingido!
                    logger.info(
                        f"Hold de {self._threshold_ms}ms atingido - "
                        f"iniciando gravação"
                    )
                    
                    if self._callback_iniciar():
                        # Transição: CONTANDO_HOLD → GRAVANDO
                        self._estado = EstadoDetector.GRAVANDO
                        self._contador_gravacao_ms = 0
                    else:
                        # Falha ao iniciar (ex: microfone indisponível)
                        logger.warning("Falha ao iniciar gravação - retornando para AGUARDANDO")
                        self._estado = EstadoDetector.AGUARDANDO
                        # Retorna para polling lento
                        self._timer.setInterval(INTERVALO_POLLING_IDLE_MS)
            else:
                # Tecla solta antes do threshold - toque acidental
                logger.debug(
                    f"CapsLock solta após {self._contador_hold_ms}ms "
                    f"(< {self._threshold_ms}ms) - ignorando"
                )
                self._estado = EstadoDetector.AGUARDANDO
                self._contador_hold_ms = 0
                # Retorna para polling lento
                self._timer.setInterval(INTERVALO_POLLING_IDLE_MS)
        
        elif self._estado == EstadoDetector.GRAVANDO:
            self._contador_gravacao_ms += intervalo_atual
            
            if not tecla_pressionada:
                # Tecla solta - parar gravação
                logger.info(
                    f"CapsLock solta após gravação de "
                    f"{self._contador_gravacao_ms}ms - parando"
                )
                self._callback_parar()
                self._estado = EstadoDetector.AGUARDANDO
                self._contador_gravacao_ms = 0
                # Retorna para polling lento
                self._timer.setInterval(INTERVALO_POLLING_IDLE_MS)
            
            elif self._contador_gravacao_ms >= DURACAO_MAXIMA_GRAVACAO_MS:
                # Proteção: gravação excessivamente longa
                logger.warning(
                    f"Gravação atingiu limite máximo de "
                    f"{DURACAO_MAXIMA_GRAVACAO_MS // 1000}s - parando automaticamente"
                )
                self._callback_parar()
                self._estado = EstadoDetector.AGUARDANDO
                self._contador_gravacao_ms = 0
                # Retorna para polling lento
                self._timer.setInterval(INTERVALO_POLLING_IDLE_MS)
