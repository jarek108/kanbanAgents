import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add tools to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tools'))
from engine_terminal import TerminalEngine

class TestEngineTerminal(unittest.TestCase):

    def setUp(self):
        self.engine = TerminalEngine()

    @patch('win32gui.IsWindowVisible')
    @patch('win32gui.GetWindowText')
    @patch('win32gui.EnumWindows')
    def test_get_window_list(self, mock_enum, mock_get_text, mock_visible):
        mock_visible.return_value = True
        mock_get_text.side_effect = ["Window 1"]
        def side_effect(handler, ctx): handler(101, None)
        mock_enum.side_effect = side_effect
        windows = self.engine.get_window_list()
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0][0], "Window 1")

    def test_connect(self):
        with patch('engine_terminal.save_config'):
            self.engine.connect(999, "MyTerm")
            self.assertEqual(self.engine.connected_hwnd, 999)

if __name__ == '__main__':
    unittest.main()