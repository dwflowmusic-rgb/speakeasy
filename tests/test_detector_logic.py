
import sys
import unittest
from unittest.mock import MagicMock, call

# Mock setup (same as reproduce_issue.py)
mock_ctypes = MagicMock()
mock_user32 = MagicMock()
mock_ctypes.windll.user32 = mock_user32
sys.modules['ctypes'] = mock_ctypes

mock_qt = MagicMock()
sys.modules['PySide6'] = mock_qt
sys.modules['PySide6.QtCore'] = mock_qt

class MockQTimer:
    def __init__(self, parent=None):
        self._interval = 0
        self.timeout = MagicMock()
        self.timeout.connect = MagicMock()

    def start(self, ms):
        self._interval = ms

    def stop(self):
        pass

    def deleteLater(self):
        pass

    def interval(self):
        return self._interval

    def setInterval(self, ms):
        self._interval = ms

mock_qt.QTimer = MockQTimer
mock_qt.QObject = MagicMock

# Import Class
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.detector_tecla import DetectorCapsLock, EstadoDetector

class TestDetectorLogic(unittest.TestCase):
    def setUp(self):
        self.cb_start = MagicMock(return_value=True)
        self.cb_stop = MagicMock()
        self.detector = DetectorCapsLock(self.cb_start, self.cb_stop, threshold_ms=500)
        # Mock user32 inside the instance usage context?
        # Actually user32 is global in module. We mocked it via sys.modules.
        self.mock_user32 = mock_user32

    def test_logic_flow(self):
        # 1. Start - Should use Idle Interval
        self.detector.iniciar()
        timer = self.detector._timer
        self.assertEqual(timer.interval(), 100, "Should start with IDLE interval (100ms)")

        # 2. Simulate Key Press (First Poll)
        # GetAsyncKeyState returns short with high bit set if key is down.
        # 0x8000 is -32768 in signed short, but ctypes handles checking differently.
        # The code uses `bool(estado & 0x8000)`.
        self.mock_user32.GetAsyncKeyState.return_value = 0x8000

        # Run callback
        self.detector._verificar_estado_tecla()

        # Check State Transition
        self.assertEqual(self.detector._estado, EstadoDetector.CONTANDO_HOLD)
        # Should have switched to ACTIVE interval
        self.assertEqual(timer.interval(), 20, "Should switch to ACTIVE interval (20ms)")
        # Should have credited the previous interval (100ms)
        self.assertEqual(self.detector._contador_hold_ms, 100)

        # 3. Simulate Hold (Next Polls)
        # Interval is now 20.

        # Poll 2: T+20ms (Total 120)
        self.detector._verificar_estado_tecla()
        self.assertEqual(self.detector._contador_hold_ms, 120)

        # Poll 3: T+20ms (Total 140)
        self.detector._verificar_estado_tecla()
        self.assertEqual(self.detector._contador_hold_ms, 140)

        # Jump ahead to threshold
        # We need 500ms. Current 140. Need 360 more. 360/20 = 18 polls.
        for _ in range(18):
            self.detector._verificar_estado_tecla()

        self.assertEqual(self.detector._contador_hold_ms, 500)

        # Next poll triggers
        self.detector._verificar_estado_tecla() # 520ms

        # Should have triggered start callback
        self.cb_start.assert_called_once()
        self.assertEqual(self.detector._estado, EstadoDetector.GRAVANDO)

        # 4. Release Key
        self.mock_user32.GetAsyncKeyState.return_value = 0x0000

        self.detector._verificar_estado_tecla()

        # Should stop
        self.cb_stop.assert_called_once()
        self.assertEqual(self.detector._estado, EstadoDetector.AGUARDANDO)

        # Should switch back to IDLE interval
        self.assertEqual(timer.interval(), 100, "Should revert to IDLE interval")

if __name__ == '__main__':
    unittest.main()
