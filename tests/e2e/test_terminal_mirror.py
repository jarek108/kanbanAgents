import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add tools/system to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tools', 'system'))
from terminal_core import TerminalCore

class TestTerminalMirrorFlow(unittest.TestCase):
    """
    E2E Test for the terminal mirroring and update logic.
    """

    def setUp(self):
        with patch('terminal_core.TerminalCore.load_config', return_value={}):
            self.core = TerminalCore()

    @patch('subprocess.Popen')
    def test_mirror_update_flow(self, mock_popen):
        # 1. Connect to a terminal
        self.core.connect_to_hwnd(1234, "MirrorTerm")
        
        # 2. Simulate UIA capture returning new text
        # Mocking the powershell execution result
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"New Terminal Content\nUser@Host:~$", b"")
        mock_popen.return_value = mock_process
        
        content = self.core.get_buffer_text()
        self.assertEqual(content, "New Terminal Content\nUser@Host:~$")

        # 3. Verify interaction - sending a command
        with patch('win32gui.IsWindow', return_value=True), \
             patch('win32gui.ShowWindow'), \
             patch('win32gui.SetForegroundWindow'), \
             patch('win32gui.IsIconic', return_value=False), \
             patch('pyautogui.write') as mock_write:
            
            success = self.core.send_command("echo hello")
            self.assertTrue(success)
            mock_write.assert_called_with("echo hello\n", interval=0.01)

if __name__ == '__main__':
    unittest.main()
