
import sys
from unittest.mock import MagicMock, patch
import unittest
import numpy as np
import os

# Mock sounddevice before import
mock_sd = MagicMock()
sys.modules['sounddevice'] = mock_sd

# Mock scipy.io.wavfile
mock_wavfile = MagicMock()
sys.modules['scipy.io.wavfile'] = mock_wavfile

# Now import the class
try:
    from core.captura_audio import CapturadorAudio, TAXA_AMOSTRAGEM, CANAIS
except ImportError as e:
    print(f"ImportError: {e}")
    # If imports fail (e.g. logger), we might need to mock more
    sys.exit(1)

class TestCapturadorAudioOptimized(unittest.TestCase):
    def setUp(self):
        self.capturador = CapturadorAudio()
        # Mock _stream to avoid AttributeError when accessing it
        self.capturador._stream = MagicMock()

    def test_initialization(self):
        # Initial state
        self.assertFalse(self.capturador.esta_gravando)

    def test_iniciar_gravacao_allocates_buffer(self):
        # Mock sd.query_devices to avoid error
        mock_sd.default.device = [0, 1]
        mock_sd.query_devices.return_value = {'name': 'Mock Mic'}

        self.capturador.iniciar_gravacao()

        self.assertTrue(self.capturador.esta_gravando)
        # Check if buffer is allocated as numpy array
        self.assertIsInstance(self.capturador._buffer, np.ndarray, "Buffer should be a numpy array")
        # Check buffer size (should be approx 60s * 16000 = 960000)
        self.assertGreaterEqual(self.capturador._buffer.shape[0], 16000 * 10, "Buffer should be pre-allocated with decent size")
        self.assertEqual(self.capturador._buffer_idx, 0, "Buffer index should be 0")

    def test_callback_writes_to_buffer(self):
        # Manually setup buffer to test callback independently
        buffer_size = 2048
        self.capturador._buffer = np.zeros((buffer_size, CANAIS), dtype=np.int16)
        self.capturador._buffer_idx = 0

        # Create chunk
        chunk_size = 512
        chunk = np.full((chunk_size, CANAIS), 100, dtype=np.int16)

        self.capturador._callback_audio(chunk, chunk_size, {}, None)

        # Verify index updated
        self.assertEqual(self.capturador._buffer_idx, chunk_size)
        # Verify data written
        written_data = self.capturador._buffer[:chunk_size]
        self.assertTrue(np.array_equal(written_data, chunk))

    def test_callback_resizes_buffer(self):
        # Setup small buffer
        self.capturador._buffer = np.zeros((100, CANAIS), dtype=np.int16)
        self.capturador._buffer_idx = 0

        # Incoming chunk larger than buffer
        chunk = np.full((150, CANAIS), 100, dtype=np.int16)

        self.capturador._callback_audio(chunk, 150, {}, None)

        # Verify resize
        self.assertGreaterEqual(self.capturador._buffer.shape[0], 150)
        self.assertEqual(self.capturador._buffer_idx, 150)
        self.assertTrue(np.array_equal(self.capturador._buffer[:150], chunk))

    def test_parar_gravacao_saves_correct_slice(self):
        self.capturador._gravando = True
        self.capturador._tempo_inicio = 123456789.0

        # Setup buffer with some data
        self.capturador._buffer = np.zeros((1000, CANAIS), dtype=np.int16)
        data_len = 500
        real_data = np.full((data_len, CANAIS), 77, dtype=np.int16)
        self.capturador._buffer[:data_len] = real_data
        self.capturador._buffer_idx = data_len

        # Call stop
        with patch('os.path.getsize', return_value=1000), \
             patch('os.remove'), \
             patch('time.time', return_value=123456789.0 + 10.0):
            caminho, duracao = self.capturador.parar_gravacao()

        # Verify wavfile.write was called with correct data
        args, _ = mock_wavfile.write.call_args
        filename, rate, data = args

        self.assertEqual(rate, TAXA_AMOSTRAGEM)
        self.assertEqual(data.shape[0], data_len)
        self.assertTrue(np.array_equal(data, real_data))

if __name__ == '__main__':
    unittest.main()
