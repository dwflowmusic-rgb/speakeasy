# -*- coding: utf-8 -*-
"""
Módulo de Gerenciamento de Clipboard do VoiceFlow Transcriber.

Copia texto para clipboard Windows usando QClipboard nativo do Qt.
Garante thread-safety e validação de escrita.
"""

from typing import Optional, Callable
import threading
import time

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from core.logger import obter_logger

logger = obter_logger('clipboard')

# Callback para notificações (será configurado pela UI)
_callback_notificacao: Optional[Callable[[str, str], None]] = None


def registrar_callback_notificacao(callback: Callable[[str, str], None]) -> None:
    """
    Registra callback para exibir notificações via UI (thread-safe).
    
    Args:
        callback: Função que recebe (titulo, mensagem)
    """
    global _callback_notificacao
    _callback_notificacao = callback
    logger.info("Callback de notificação registrado")


def _copiar_impl(texto: str) -> bool:
    """Implementação interna da cópia via Win32 API."""
    import ctypes
    from ctypes import wintypes, c_size_t, c_void_p, c_wchar_p
    
    # Win32 API
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    
    # Configura tipos de retorno e argumentos
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = c_void_p
    
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.restype = wintypes.HGLOBAL
    
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL
    
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = wintypes.BOOL
    
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    
    # Constantes
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002
    
    try:
        # Abre clipboard com retry
        for tentativa in range(10):
            if user32.OpenClipboard(None):
                break
            logger.debug(f"Clipboard ocupado, tentativa {tentativa + 1}/10")
            import time
            time.sleep(0.05)
        else:
            logger.error("Não foi possível abrir clipboard após 10 tentativas")
            return False
        
        try:
            # Limpa clipboard
            if not user32.EmptyClipboard():
                logger.error("Falha ao limpar clipboard")
                return False
            
            # Prepara texto como UTF-16 com null terminator
            texto_com_null = texto + '\0'
            texto_bytes = texto_com_null.encode('utf-16-le')
            tamanho = len(texto_bytes)
            
            # Aloca memória global
            h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, tamanho)
            if not h_mem:
                erro = ctypes.get_last_error()
                logger.error(f"Falha ao alocar memória: erro {erro}")
                return False
            
            # Lock memória e copia dados
            p_mem = kernel32.GlobalLock(h_mem)
            if not p_mem:
                erro = ctypes.get_last_error()
                kernel32.GlobalFree(h_mem)
                logger.error(f"Falha ao fazer lock: erro {erro}")
                return False
            
            # Copia bytes para memória alocada
            ctypes.memmove(p_mem, texto_bytes, tamanho)
            kernel32.GlobalUnlock(h_mem)
            
            # Define dados no clipboard
            result = user32.SetClipboardData(CF_UNICODETEXT, h_mem)
            if not result:
                erro = ctypes.get_last_error()
                kernel32.GlobalFree(h_mem)
                logger.error(f"Falha ao definir clipboard data: erro {erro}")
                return False
            
            logger.info(f"✅ Clipboard atualizado via Win32 API: {len(texto)} caracteres")
            return True
            
        finally:
            user32.CloseClipboard()
            
    except Exception as e:
        logger.error(f"Erro ao copiar para clipboard: {e}")
        return False


def copiar_para_clipboard(texto: str) -> bool:
    """
    Copia texto para clipboard usando Win32 API direta.

    Se chamado da thread principal, executa a operação em uma thread secundária
    para evitar congelamento da UI durante os retries (sleep), mas aguarda
    a conclusão processando eventos da UI (QApplication.processEvents).

    Args:
        texto: Texto a ser copiado

    Returns:
        True se cópia foi bem-sucedida
    """
    app = QApplication.instance()

    # Se estiver na thread principal e temos uma QApplication, usamos thread dedicada
    if app and threading.current_thread() is threading.main_thread():
        result_container = []

        def worker():
            res = _copiar_impl(texto)
            result_container.append(res)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

        # Aguarda thread terminar mantendo a UI responsiva
        while t.is_alive():
            app.processEvents()
            time.sleep(0.01)  # Yield para CPU

        t.join()  # Garante que terminou
        return result_container[0] if result_container else False

    else:
        # Se já estiver em background ou sem app, roda direto
        return _copiar_impl(texto)


def exibir_notificacao(titulo: str, mensagem: str, duracao: int = 3) -> bool:
    """
    Exibe notificação via callback registrado (thread-safe).
    
    Args:
        titulo: Título da notificação
        mensagem: Corpo da mensagem
        duracao: Duração em segundos (ignorado, usa padrão do sistema)
        
    Returns:
        True se notificação foi enviada com sucesso
    """
    try:
        if _callback_notificacao:
            _callback_notificacao(titulo, mensagem)
            logger.info(f"Notificação enviada: {titulo}")
            return True
        else:
            logger.warning(f"Callback de notificação não configurado. Mensagem: {titulo} - {mensagem}")
            return False
    except Exception as e:
        logger.warning(f"Erro ao exibir notificação: {e}")
        return False


def notificar_sucesso(mensagem: str = "Transcrição pronta e disponível no clipboard") -> None:
    """
    Exibe notificação de transcrição concluída com sucesso.
    
    NOTA: Notificação toast desabilitada - Widget de Status mostra o feedback.
    
    Args:
        mensagem: Mensagem personalizada (opcional)
    """
    # Notificação toast desabilitada - o StatusWidget já mostra o feedback visual
    # Se quiser reabilitar, descomente a linha abaixo:
    # exibir_notificacao("VoiceFlow Transcriber", mensagem)
    logger.info(f"Sucesso: {mensagem}")


def notificar_erro(mensagem: str) -> None:
    """
    Exibe notificação de erro.
    
    Args:
        mensagem: Descrição do erro para o usuário
    """
    exibir_notificacao(
        "VoiceFlow - Erro",
        mensagem
    )
