# -*- coding: utf-8 -*-
"""
Módulo de Captura de Áudio do VoiceFlow Transcriber.

Captura áudio do microfone padrão Windows em formato WAV 16kHz mono PCM 16-bit.
Otimizado para baixo consumo de memória com buffer numpy dinâmico.
"""

import os
import tempfile
import time
import threading
from datetime import datetime
from typing import Optional, Tuple

import numpy as np
import sounddevice as sd
from scipy.io import wavfile

from core.logger import obter_logger

# Configurações de áudio compatíveis com Groq Whisper
TAXA_AMOSTRAGEM = 16000  # 16kHz
CANAIS = 1  # Mono
DTYPE = np.int16  # PCM 16-bit
DURACAO_MINIMA_SEGUNDOS = 0.5  # Descarta gravações < 500ms

logger = obter_logger('captura_audio')


class CapturadorAudio:
    """
    Gerencia captura de áudio do microfone Windows.
    
    Implementa buffer dinâmico em memória que cresce conforme gravação.
    Salva arquivo WAV temporário quando gravação é finalizada.
    """
    
    def __init__(self):
        self._gravando: bool = False
        self._buffer: list = []
        self._stream: Optional[sd.InputStream] = None
        self._tempo_inicio: Optional[float] = None
        self._dispositivo: Optional[int] = None
        self._save_event = threading.Event()
        self._save_event.set()  # Inicialmente liberado
        
    def _callback_audio(self, indata: np.ndarray, frames: int, 
                        time_info: dict, status: sd.CallbackFlags) -> None:
        """
        Callback chamado pelo sounddevice para cada chunk de áudio.
        
        Args:
            indata: Array numpy com dados de áudio
            frames: Número de frames no chunk
            time_info: Informações de timing
            status: Flags de status (overflow, underflow)
        """
        if status:
            logger.warning(f"Status do stream de áudio: {status}")
        
        # Adiciona chunk ao buffer (cópia para evitar referência)
        self._buffer.append(indata.copy())
    
    def iniciar_gravacao(self) -> bool:
        """
        Inicia captura de áudio do microfone padrão.
        
        Returns:
            True se gravação iniciou com sucesso, False caso contrário
        """
        if self._gravando:
            logger.warning("Tentativa de iniciar gravação já em andamento")
            return False
        
        try:
            # Limpa buffer anterior
            self._buffer = []
            
            # Obtém dispositivo padrão
            self._dispositivo = sd.default.device[0]
            dispositivo_info = sd.query_devices(self._dispositivo)
            logger.info(f"Usando microfone: {dispositivo_info['name']}")
            
            # Configura e inicia stream
            self._stream = sd.InputStream(
                samplerate=TAXA_AMOSTRAGEM,
                channels=CANAIS,
                dtype=DTYPE,
                callback=self._callback_audio,
                blocksize=1024  # Chunks de ~64ms
            )
            self._stream.start()
            
            self._gravando = True
            self._tempo_inicio = time.time()
            
            logger.info(f"Gravação iniciada - Taxa: {TAXA_AMOSTRAGEM}Hz, Canais: {CANAIS}")
            return True
            
        except sd.PortAudioError as e:
            logger.error(f"Erro ao acessar microfone: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado ao iniciar gravação: {e}")
            return False
    
    def parar_gravacao(self) -> Tuple[Optional[str], float]:
        """
        Para captura de áudio e salva arquivo WAV temporário.
        
        Returns:
            Tupla com (caminho_arquivo_wav, duracao_segundos).
            Retorna (None, 0) se gravação foi muito curta ou houve erro.
        """
        if not self._gravando:
            logger.warning("Tentativa de parar gravação não iniciada")
            return None, 0.0
        
        try:
            # Para stream
            self._stream.stop()
            self._stream.close()
            self._gravando = False
            
            # Calcula duração
            duracao = time.time() - self._tempo_inicio
            logger.info(f"Gravação parada - Duração: {duracao:.2f}s")
            
            # Verifica duração mínima (evita acionamentos acidentais)
            if duracao < DURACAO_MINIMA_SEGUNDOS:
                logger.info(f"Gravação descartada - muito curta ({duracao:.2f}s < {DURACAO_MINIMA_SEGUNDOS}s)")
                self._buffer = []
                return None, 0.0
            
            # Concatena buffer em array único
            if not self._buffer:
                logger.warning("Buffer de áudio vazio")
                return None, 0.0
            
            audio_completo = np.concatenate(self._buffer, axis=0)
            self._buffer = []  # Libera memória
            
            # Gera nome único para arquivo temporário
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"voiceflow_{timestamp}.wav"
            caminho_wav = os.path.join(tempfile.gettempdir(), nome_arquivo)
            
            # Inicia salvamento em background
            self._save_event.clear()
            thread = threading.Thread(
                target=self._salvar_wav_worker,
                args=(caminho_wav, audio_completo),
                daemon=True
            )
            thread.start()
            
            return caminho_wav, duracao
            
        except Exception as e:
            logger.error(f"Erro ao parar gravação: {e}")
            self._gravando = False
            self._buffer = []
            return None, 0.0

    def _salvar_wav_worker(self, caminho_wav: str, audio_completo: np.ndarray) -> None:
        """Worker thread para salvar arquivo WAV."""
        try:
            # Salva arquivo WAV
            wavfile.write(caminho_wav, TAXA_AMOSTRAGEM, audio_completo)

            # Valida arquivo criado
            if os.path.exists(caminho_wav):
                tamanho = os.path.getsize(caminho_wav)
                logger.info(f"Arquivo WAV salvo: {caminho_wav} ({tamanho} bytes)")

                if tamanho == 0:
                    logger.error("Arquivo WAV criado com tamanho zero")
                    # Nota: Não removemos o arquivo aqui para evitar race conditions
                    # O consumidor detectará arquivo vazio
            else:
                logger.error(f"Arquivo WAV não foi criado: {caminho_wav}")

        except Exception as e:
            logger.error(f"Erro ao salvar arquivo em background: {e}")
        finally:
            self._save_event.set()

    def aguardar_salvamento(self, timeout: Optional[float] = None) -> bool:
        """
        Aguarda finalização do salvamento do arquivo.

        Args:
            timeout: Tempo máximo de espera em segundos

        Returns:
            True se salvamento concluiu, False se houve timeout
        """
        return self._save_event.wait(timeout)
    
    @property
    def esta_gravando(self) -> bool:
        """Retorna True se gravação está em andamento."""
        return self._gravando
    
    @property
    def duracao_atual(self) -> float:
        """Retorna duração da gravação atual em segundos."""
        if self._gravando and self._tempo_inicio:
            return time.time() - self._tempo_inicio
        return 0.0


def limpar_arquivo_temporario(caminho: str) -> bool:
    """
    Remove arquivo WAV temporário após processamento.
    
    Args:
        caminho: Caminho completo do arquivo a ser removido
        
    Returns:
        True se arquivo foi removido com sucesso
    """
    try:
        if os.path.exists(caminho):
            os.remove(caminho)
            logger.info(f"Arquivo temporário removido: {caminho}")
            return True
        return False
    except Exception as e:
        logger.warning(f"Falha ao remover arquivo temporário: {e}")
        return False
