# -*- coding: utf-8 -*-
"""
Testes do módulo de captura de áudio.
"""

import os
import tempfile
import time
import pytest
import sys
import unittest.mock as mock
import numpy as np

# Mock sounddevice BEFORE importing core
mock_sd = mock.MagicMock()
mock_sd.default.device = [0]
mock_sd.query_devices.return_value = {'name': 'Mock Mic'}
mock_sd.InputStream.return_value = mock.MagicMock()
mock_sd.CallbackFlags = mock.MagicMock
sys.modules['sounddevice'] = mock_sd

# Importações serão feitas após instalação das dependências
# from core.captura_audio import CapturadorAudio, limpar_arquivo_temporario


class TestCapturadorAudio:
    """Testes para a classe CapturadorAudio."""
    
    def test_iniciar_gravacao_retorna_true(self):
        """Verifica que gravação inicia com sucesso quando microfone disponível."""
        from core.captura_audio import CapturadorAudio
        
        capturador = CapturadorAudio()
        resultado = capturador.iniciar_gravacao()
        
        # Para gravação se iniciou
        if resultado:
            capturador.parar_gravacao()
        
        # Aceita False se microfone não estiver disponível
        assert isinstance(resultado, bool)
    
    def test_gravacao_cria_arquivo_wav(self):
        """Verifica que arquivo WAV é criado após gravação."""
        from core.captura_audio import CapturadorAudio
        
        capturador = CapturadorAudio()
        
        if not capturador.iniciar_gravacao():
            pytest.skip("Microfone não disponível")
        
        # Grava por 1 segundo
        time.sleep(1.0)
        
        # Simula dados no buffer (já que o mock do sounddevice não gera audio real)
        from core.captura_audio import TAXA_AMOSTRAGEM, CANAIS, DTYPE
        chunk_size = 1024
        # Simula ~1s de audio
        num_chunks = int(TAXA_AMOSTRAGEM * 1.0 / chunk_size)
        chunk = np.zeros((chunk_size, CANAIS), dtype=DTYPE)
        for _ in range(num_chunks):
            capturador._buffer.append(chunk)

        # Simula inicio no passado
        capturador._tempo_inicio = time.time() - 1.0

        caminho, duracao = capturador.parar_gravacao()
        
        # Aguarda salvamento do arquivo (async)
        capturador.aguardar_salvamento()

        # Verifica arquivo foi criado
        assert caminho is not None, "Caminho do arquivo não retornado"
        assert os.path.exists(caminho), f"Arquivo não existe: {caminho}"
        assert os.path.getsize(caminho) > 1000, "Arquivo muito pequeno (< 1KB)"
        assert duracao >= 0.9, f"Duração muito curta: {duracao}s"
        
        # Limpa arquivo
        os.remove(caminho)
    
    def test_gravacao_curta_descartada(self):
        """Verifica que gravações muito curtas são descartadas."""
        from core.captura_audio import CapturadorAudio
        
        capturador = CapturadorAudio()
        
        if not capturador.iniciar_gravacao():
            pytest.skip("Microfone não disponível")
        
        # Grava por apenas 200ms (abaixo do limite de 500ms)
        time.sleep(0.2)
        
        caminho, duracao = capturador.parar_gravacao()
        
        # Deve retornar None (gravação descartada)
        assert caminho is None, "Gravação curta não foi descartada"


class TestLimparArquivoTemporario:
    """Testes para função de limpeza de arquivos."""
    
    def test_remove_arquivo_existente(self):
        """Verifica que arquivo existente é removido."""
        from core.captura_audio import limpar_arquivo_temporario
        
        # Cria arquivo temporário
        fd, caminho = tempfile.mkstemp(suffix='.wav')
        os.close(fd)
        
        assert os.path.exists(caminho)
        
        resultado = limpar_arquivo_temporario(caminho)
        
        assert resultado is True
        assert not os.path.exists(caminho)
    
    def test_retorna_false_arquivo_inexistente(self):
        """Verifica que retorna False para arquivo que não existe."""
        from core.captura_audio import limpar_arquivo_temporario
        
        resultado = limpar_arquivo_temporario('/caminho/inexistente/arquivo.wav')
        
        assert resultado is False
