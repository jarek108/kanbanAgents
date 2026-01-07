import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add tools to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tools'))
import engine_projects

class TestEngineProjects(unittest.TestCase):

    def setUp(self):
        # We must patch the function where it IS, not where it is imported
        self.events_patcher = patch('engine_projects.engine_events')
        self.events_patcher.start()

    def tearDown(self):
        self.events_patcher.stop()

    @patch('engine_projects.load_projects', return_value=[])
    @patch('engine_projects.save_projects')
    def test_add_project(self, mock_save, mock_load):
        engine_projects.add_project("new", "/path", "kb")
        mock_save.assert_called_once()

    @patch('engine_projects._git_cmd')
    def test_get_git_info(self, mock_git):
        # 6 calls: is_git, branch, root, commit, remote, status
        mock_git.side_effect = ["true", "main", "/root", "abc123", "", ""]
        with patch('os.path.exists', return_value=True):
            branch, status, root, commit, remote = engine_projects.get_git_info("/path")
            self.assertEqual(branch, "main")
            self.assertEqual(commit, "abc123")

if __name__ == '__main__':
    unittest.main()
