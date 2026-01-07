import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Add tools/system to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tools', 'system'))
from orchestrator_core import OrchestratorCore

class TestOrchestratorFlow(unittest.TestCase):
    """
    E2E Test simulating the flow from adding a project to starting a worker.
    """

    def setUp(self):
        # Prevent actual file writes during tests
        with patch('terminal_core.TerminalCore.load_config', return_value={}):
            self.core = OrchestratorCore()
        self.core.projects = []

    @patch('subprocess.check_output')
    @patch('subprocess.Popen')
    @patch('orchestrator_core.OrchestratorCore.save_projects')
    def test_full_agent_onboarding_flow(self, mock_save, mock_popen, mock_git):
        # 1. User adds a project
        new_proj_name = "secret-project"
        new_proj_path = "C:\\repos\\secret"
        kanban_name = "secret-board"
        
        self.core.add_project(new_proj_name, new_proj_path, kanban_name)
        self.assertEqual(len(self.core.projects), 1)
        self.assertEqual(self.core.projects[0]['name'], new_proj_name)

        # 2. Orchestrator fetches Git info for the dashboard
        mock_git.side_effect = ["true", "feature-branch", "M file.txt"]
        with patch('os.path.exists', return_value=True):
            branch, status = self.core.get_git_info(new_proj_path)
            self.assertEqual(branch, "feature-branch")
            self.assertEqual(status, "Modified")

        # 3. User selects a role and clicks 'Start Worker'
        role = "manager"
        with patch('os.path.exists', return_value=True):
            window_title = self.core.launch_worker(self.core.projects[0], role)
            self.assertEqual(window_title, f"Agent_{new_proj_name}_{role}")
            self.assertTrue(mock_popen.called)

        # 4. Mirror logic finds the window and connects
        # (Simulating get_window_list finding the launched window)
        with patch('win32gui.IsWindowVisible', return_value=True), \
             patch('win32gui.GetWindowText', return_value=window_title), \
             patch('win32gui.EnumWindows', side_effect=lambda h, c: h(555, None)):
            
            windows = self.core.get_window_list()
            found = next((h for t, h in windows if window_title in t), None)
            self.assertEqual(found, 555)
            
            # Connect
            connected = self.core.connect_to_hwnd(found, window_title)
            self.assertTrue(connected)
            self.assertEqual(self.core.connected_hwnd, 555)

if __name__ == '__main__':
    unittest.main()
