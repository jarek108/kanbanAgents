import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add tools/system to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tools', 'system'))
from terminal_core import TerminalCore

class TestTerminalCore(unittest.TestCase):

    def setUp(self):
        self.core = TerminalCore()
        self.core.config = {
            "last_title": "TestTerminal",
            "sync_interval_ms": 1000,
            "auto_sync": True
        }

    @patch('win32gui.IsWindowVisible')
    @patch('win32gui.GetWindowText')
    @patch('win32gui.EnumWindows')
    def test_get_window_list(self, mock_enum, mock_get_text, mock_visible):
        mock_visible.return_value = True
        mock_get_text.side_effect = ["Window 1", "Window 2"]
        
        # Simulate EnumWindows calling the handler
        def side_effect(handler, ctx):
            handler(101, None)
            handler(102, None)
        mock_enum.side_effect = side_effect

        windows = self.core.get_window_list()
        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0][0], "Window 1")
        self.assertEqual(windows[1][1], 102)

    def test_connect_to_hwnd(self):
        with patch.object(self.core, 'save_config') as mock_save:
            self.core.connect_to_hwnd(999, "MyTerm")
            self.assertEqual(self.core.connected_hwnd, 999)
            self.assertEqual(self.core.connected_title, "MyTerm")
            mock_save.assert_called()

    @patch('win32gui.IsWindow')
    @patch('pyautogui.write')
    def test_send_command_success(self, mock_write, mock_is_window):
        mock_is_window.return_value = True
        self.core.connected_hwnd = 123
        
        with patch('win32gui.SetForegroundWindow'), \
             patch('win32gui.ShowWindow'), \
             patch('win32gui.IsIconic', return_value=False):
            
            result = self.core.send_command("ls")
            self.assertTrue(result)
            mock_write.assert_called_with("ls\n", interval=0.01)

if __name__ == '__main__':
    unittest.main()
