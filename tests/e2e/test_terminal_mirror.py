import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add tools to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tools'))
from engine_terminal import TerminalEngine

class TestTerminalMirrorFlow(unittest.TestCase):

    @patch('subprocess.Popen')
    def test_mirror_update_flow(self, mock_popen):
        engine = TerminalEngine()
        with patch('engine_terminal.save_config'):
            engine.connect(1234, "MirrorTerm")
        
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"New Terminal Content\nUser@Host:~$ ", b"")
        mock_popen.return_value = mock_process
        
        content = engine.get_buffer_text()
        self.assertEqual(content, "New Terminal Content\nUser@Host:~$")

if __name__ == '__main__':
    unittest.main()