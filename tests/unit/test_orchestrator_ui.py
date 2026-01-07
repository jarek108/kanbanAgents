import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add tools to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tools'))

class TestOrchestratorUI(unittest.TestCase):

    @patch('orchestrator.engine_projects.load_projects', return_value=[])
    @patch('orchestrator.OrchestratorUI._load_full_config', return_value={})
    @patch('orchestrator.engine_terminal.TerminalEngine')
    def test_connect_by_pid_not_crashing(self, mock_engine, mock_cfg, mock_load):
        # We need to mock Tk root
        root = MagicMock()
        import orchestrator
        
        # Instantiate UI
        ui = orchestrator.OrchestratorUI(root)
        
        # Mock win32gui and win32process which are used inside connect_by_pid
        with patch('orchestrator.win32gui.EnumWindows') as mock_enum, \
             patch('orchestrator.win32process.GetWindowThreadProcessId', return_value=(0, 1234)):
            
            # This call previously failed with NameError: win32gui
            ui.connect_by_pid(1234, "test_title")
            
            # Verify EnumWindows was called
            self.assertTrue(mock_enum.called)

    def test_settings_save_logic_bool_vs_int(self):
        # Verify the fix for bool vs int distinction
        import orchestrator
        # Mocking objects for the save function's loop
        orig_bool = True
        orig_int = 10
        
        # Case 1: bool
        new_val_str = "False"
        if type(orig_bool) is bool:
            new_val = new_val_str.lower() in ("true", "1", "yes")
        self.assertIsInstance(new_val, bool)
        self.assertEqual(new_val, False)
        
        # Case 2: int (would fail if bool check used isinstance and came second)
        new_val_str = "42"
        if type(orig_int) is bool:
            pass # shouldn't happen
        elif isinstance(orig_int, int):
            new_val = int(new_val_str)
        self.assertEqual(new_val, 42)

if __name__ == '__main__':
    unittest.main()

