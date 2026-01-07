import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add tools to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tools'))
import engine_projects

class TestLaunchWorker(unittest.TestCase):

    def setUp(self):
        self.events_patcher = patch('engine_projects.engine_events')
        self.events_patcher.start()

    def tearDown(self):
        self.events_patcher.stop()

    @patch('subprocess.Popen')
    def test_launch_worker_path_verification(self, mock_popen):
        """Test that the role file path constructed is correct and exists."""
        project = {"name": "test_proj", "local_path": os.getcwd()}
        role = "manager"
        
        # In engine_projects.py:
        # AGENT_DEFS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agent_definitions")
        
        title = engine_projects.launch_worker(project, role)
        
        # Check title
        self.assertEqual(title, "Agent_test_proj_manager")
        
        # Check if subprocess was called
        self.assertTrue(mock_popen.called)
        
        # Capture the args
        args = mock_popen.call_args[0][0]
        # args is either a list (for wt) or a string (for start)
        
        # If it tried 'wt'
        if isinstance(args, list):
            cmd_part = args[-1] # cmd /k [this]
            # Check if role_file in cmd_part exists
            # cmd_part is: gemini --prompt "C:\...\manager.md"
            import re
            match = re.search(r'--prompt "(.*?)"', cmd_part)
            if match:
                role_path = match.group(1)
                self.assertTrue(os.path.exists(role_path), f"Role file does not exist at: {role_path}")
            else:
                self.fail("Could not find role path in launch command")

if __name__ == '__main__':
    unittest.main()
