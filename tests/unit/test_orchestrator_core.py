import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add tools/system to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tools', 'system'))
from orchestrator_core import OrchestratorCore

class TestOrchestratorCore(unittest.TestCase):

    def setUp(self):
        with patch('terminal_core.TerminalCore.load_config', return_value={}):
            self.core = OrchestratorCore()
        self.core.projects = [
            {"name": "test", "local_path": "/fake/path", "kanban_project_name": "kb_test"}
        ]

    def test_add_project(self):
        with patch.object(self.core, 'save_projects'):
            self.core.add_project("new", "/path", "kb")
            self.assertEqual(len(self.core.projects), 2)
            self.assertEqual(self.core.projects[1]['name'], "new")

    @patch('subprocess.check_output')
    def test_get_git_info_clean(self, mock_output):
        # Mock git commands
        mock_output.side_effect = [
            "true",      # rev-parse --is-inside-work-tree
            "main",      # branch --show-current
            ""           # status --short (empty means clean)
        ]
        
        with patch('os.path.exists', return_value=True):
            branch, status = self.core.get_git_info("/fake/path")
            self.assertEqual(branch, "main")
            self.assertEqual(status, "Clean")

    @patch('subprocess.Popen')
    def test_launch_worker(self, mock_popen):
        project = {"name": "p1", "local_path": "/path/p1"}
        role = "coder"
        
        with patch('os.path.exists', return_value=True):
            title = self.core.launch_worker(project, role)
            self.assertIn("Agent_p1_coder", title)
            self.assertTrue(mock_popen.called)

if __name__ == '__main__':
    unittest.main()
