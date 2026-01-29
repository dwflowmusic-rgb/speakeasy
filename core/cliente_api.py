# -*- coding: utf-8 -*-
"""
Módulo de Integração com APIs do VoiceFlow Transcriber.

Integra com Groq Whisper (transcrição) e Google Gemini (polimento).
Implementa timeout, retry com backoff exponencial e fallback gracioso.
"""

import time
import threading
from typing import Optional, Tuple

from groq import Groq
from google import genai
from google.genai import types

from core.logger import obter_logger

logger = obter_logger('cliente_api')

# Configurações de retry
TIMEOUT_SEGUNDOS = 15
MAX_TENTATIVAS = 3
BACKOFF_BASE = 2  # Segundos (2, 4, 8...)

# Prompt de polimento (mantém voz do falante, apenas poli imperfeições)
# Prompt de polimento (Assertivo na forma, fiel no conteúdo)
PROMPT_POLIMENTO = """Atue como um Editor de Texto Sênior.

Sua missão é transformar a transcrição de voz (que pode conter erros, gaguejos e falta de pontuação) em um texto escrito fluído, profissional e claro.

DIRETRIZES DE EDIÇÃO:
1. PONTUAÇÃO & FLUIDEZ: Adicione pontuação para criar um ritmo de leitura natural. Corrija fragmentos.
2. REMOVER RUÍDOS: Elimine repetições ("eu eu"), pausas verbalizadas ("ééé", "humm") e cacoetes ("tipo assim", "né") que poluem o texto.
3. MANTER SENTIDO: Não altere a mensagem original. Melhore A FORMA, preserve O CONTEÚDO.
4. ESTILO: Texto em prosa (parágrafos). Nunca use tópicos/bullets.

SOBRE ALUCINAÇÕES (SEGURANÇA):
- Se o texto de entrada for EXCLUSIVAMENTE ruído, música ou frases sem sentido como "Obrigado por assistir", retorne apenas: [SILENCIO]
- Caso contrário, SEMPRE tente polir e melhorar o texto, mesmo que seja curto.

SAÍDA:
Apenas o texto melhorado.

ENTRADA BRUTA:
"""


class ClienteAPI:
    """
    Cliente para integração com APIs de transcrição e polimento.
    
    Gerencia comunicação com Groq Whisper e Google Gemini.
    """
    
    def __init__(self, config: dict):
        """
        Inicializa cliente com configurações.
        
        Args:
            config: Dicionário com configurações de API (keys, modelos)
        """
        self._config = config
        
        # Inicializa cliente Groq
        self._cliente_groq = Groq(
            api_key=config['transcription']['api_key']
        )
        self._modelo_groq = config['transcription']['model']
        
        # Inicializa cliente Gemini
        self._cliente_gemini = genai.Client(
            api_key=config['polishing']['api_key']
        )
        self._modelo_gemini = config['polishing']['model']
        
        logger.info(f"ClienteAPI inicializado - Groq: {self._modelo_groq}, Gemini: {self._modelo_gemini}")
    
    def transcrever(self, caminho_audio: str, stop_event: Optional[threading.Event] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Transcreve arquivo de áudio usando Groq Whisper.
        
        Args:
            caminho_audio: Caminho do arquivo WAV
            stop_event: Evento opcional para cancelar operação durante espera
            
        Returns:
            Tupla (texto_transcrito, mensagem_erro).
            Se sucesso: (texto, None). Se falha: (None, mensagem_erro).
        """
        logger.info(f"Iniciando transcrição: {caminho_audio}")
        
        # Lê arquivo UMA VEZ antes do loop de retry
        try:
            with open(caminho_audio, "rb") as arquivo:
                audio_bytes = arquivo.read()
                nome_arquivo = caminho_audio.split("\\")[-1].split("/")[-1]
            logger.info(f"Arquivo lido: {len(audio_bytes)} bytes")
        except Exception as e:
            logger.error(f"Erro ao ler arquivo de áudio: {e}")
            return None, f"Erro ao ler arquivo: {e}"
        
        if len(audio_bytes) == 0:
            logger.error("Arquivo de áudio está vazio")
            return None, "Arquivo de áudio vazio"
        
        for tentativa in range(MAX_TENTATIVAS):
            try:
                inicio = time.time()
                
                resposta = self._cliente_groq.audio.transcriptions.create(
                    file=(nome_arquivo, audio_bytes),
                    model=self._modelo_groq,
                    temperature=0,
                    response_format="verbose_json"
                )
                
                latencia = time.time() - inicio
                texto = resposta.text
                
                # FILTRO ANTI-ALUCINAÇÃO (Groq Whisper)
                # Remove frases comuns geradas em silêncio
                alucinacoes = [
                    "Obrigado por assistir", "Thank you for watching",
                    "Legendas pela comunidade", "Subtitles by",
                    "Amara.org", "MBC"
                ]
                
                texto_check = texto.strip().lower()
                for frase in alucinacoes:
                    # Se o texto for APENAS a alucinação (ou muito curto e contiver ela)
                    if frase.lower() in texto_check and len(texto_check) < 50:
                        logger.warning(f"Alucinação de ASR detectada e removida: '{texto.strip()}'")
                        texto = ""
                        break
                
                logger.info(f"Transcrição concluída em {latencia:.2f}s - {len(texto)} caracteres")
                logger.debug(f"Texto bruto: {texto[:200]}...")
                
                return texto, None
                    
            except Exception as e:
                erro_str = str(e)
                logger.warning(f"Tentativa {tentativa + 1}/{MAX_TENTATIVAS} falhou: {erro_str}")
                
                # Verifica se é erro de quota
                if "rate_limit" in erro_str.lower() or "quota" in erro_str.lower():
                    return None, "Limite diário do Groq atingido - tente novamente amanhã"
                
                # Verifica se é erro de autenticação
                if "authentication" in erro_str.lower() or "api_key" in erro_str.lower():
                    return None, "Credenciais do Groq inválidas - verifique configuração"
                
                # Retry com backoff exponencial
                if tentativa < MAX_TENTATIVAS - 1:
                    tempo_espera = BACKOFF_BASE ** (tentativa + 1)
                    logger.info(f"Aguardando {tempo_espera}s antes de nova tentativa...")

                    if stop_event:
                        if stop_event.wait(tempo_espera):
                            logger.info("Operação cancelada durante espera.")
                            return None, "Operação cancelada pelo usuário"
                    else:
                        time.sleep(tempo_espera)
        
        return None, "Falha na transcrição após múltiplas tentativas - verifique conexão"
    
    def polir(self, texto_bruto: str, stop_event: Optional[threading.Event] = None) -> Tuple[str, bool]:
        """
        Poli texto transcrito usando Google Gemini.
        
        Args:
            texto_bruto: Transcrição bruta do áudio
            stop_event: Evento opcional para cancelar operação durante espera
            
        Returns:
            Tupla (texto_polido, foi_polido).
            Se polimento falhar, retorna texto bruto como fallback.
        """
        logger.info(f"Iniciando polimento: {len(texto_bruto)} caracteres")
        
        for tentativa in range(MAX_TENTATIVAS):
            try:
                inicio = time.time()
                
                # Monta conteúdo da requisição
                conteudo = [
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=PROMPT_POLIMENTO + texto_bruto)
                        ]
                    )
                ]
                
                # Gera resposta
                resposta = self._cliente_gemini.models.generate_content(
                    model=self._modelo_gemini,
                    contents=conteudo
                )
                
                latencia = time.time() - inicio
                texto_polido = resposta.text.strip()
                
                # Tratamento de silêncio detectado pelo Gemini
                if "[SILENCIO]" in texto_polido:
                    logger.info("Gemini detectou silêncio/ruído -> Retornando vazio")
                    return "", True
                
                logger.info(f"Polimento concluído em {latencia:.2f}s - {len(texto_polido)} caracteres")
                logger.debug(f"Texto polido: {texto_polido[:200]}...")
                
                return texto_polido, True
                
            except Exception as e:
                erro_str = str(e)
                logger.warning(f"Tentativa polimento {tentativa + 1}/{MAX_TENTATIVAS} falhou: {erro_str}")
                
                # Retry com backoff exponencial
                if tentativa < MAX_TENTATIVAS - 1:
                    tempo_espera = BACKOFF_BASE ** (tentativa + 1)
                    logger.info(f"Aguardando {tempo_espera}s antes de nova tentativa...")

                    if stop_event:
                        if stop_event.wait(tempo_espera):
                            logger.info("Operação cancelada durante espera.")
                            return texto_bruto, False
                    else:
                        time.sleep(tempo_espera)
        
        # Fallback: retorna texto bruto
        logger.warning("Polimento falhou - usando texto bruto como fallback")
        return texto_bruto, False
