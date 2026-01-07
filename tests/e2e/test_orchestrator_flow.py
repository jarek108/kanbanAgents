import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add tools to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tools'))
import engine_projects
import engine_terminal

class TestOrchestratorFlow(unittest.TestCase):

    def setUp(self):
        self.events_patcher = patch('engine_projects.engine_events')
        self.events_patcher.start()

    def tearDown(self):
        self.events_patcher.stop()

    @patch('engine_projects._git_cmd')
    @patch('subprocess.Popen')
    @patch('engine_projects.save_projects')
    @patch('engine_projects.load_projects', return_value=[])
    def test_full_agent_onboarding_flow(self, mock_load, mock_save, mock_popen, mock_git):
        # 1. Add project
        engine_projects.add_project("secret-project", "C:\\repos\\secret", "secret-board")
        
        # 2. Get Git info
        # 6 calls expected: is_git, branch, root, commit, remote, status
        mock_git.side_effect = ["true", "feature-branch", "C:\\repos\\secret", "abc123", "", ""]
        with patch('os.path.exists', return_value=True):
            branch, status, root, commit, remote = engine_projects.get_git_info("C:\\repos\\secret")
            self.assertEqual(branch, "feature-branch")

        # 3. Launch worker
        with patch('os.path.exists', return_value=True):
            window_title = engine_projects.launch_worker({"name": "p1", "local_path": "/path"}, "manager")
            self.assertEqual(window_title, "Agent_p1_manager")

        # 4. Connect mirror
        engine = engine_terminal.TerminalEngine()
        with patch('engine_terminal.save_config'):
            # Mocking get_window_list
            with patch.object(engine, 'get_window_list', return_value=[(window_title, 555)]):
                engine.connect(555, window_title)
                self.assertEqual(engine.connected_hwnd, 555)

if __name__ == '__main__':
    unittest.main()

