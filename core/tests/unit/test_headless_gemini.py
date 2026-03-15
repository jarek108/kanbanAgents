import unittest
import sys
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add core to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
from core import headless_gemini

class TestHeadlessGeminiUnit(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(os.getcwd())

    @patch('subprocess.run')
    def test_simple_question_mock(self, mock_run):
        """
        Unit test to verify that invoke_agent correctly calls the Gemini CLI
        and returns the expected result based on mocked output.
        """
        # Configure the mock to simulate a successful Gemini response
        mock_response = MagicMock()
        mock_response.returncode = 0
        mock_response.stdout = "50"
        mock_response.stderr = ""
        mock_run.return_value = mock_response

        prompt = "how many states are in the usa, just give a number no words or other remarks or you break the system"
        
        # Act
        success, stdout, stderr = headless_gemini.invoke_agent(
            workspace_path=self.workspace,
            prompt=prompt,
            model="gemini-3-flash-preview"
        )
        
        # Assert
        self.assertTrue(success)
        self.assertEqual(stdout.strip(), "50")
        
        # Verify that subprocess.run was called with correct arguments
        # On Windows, gemini might resolve to a .cmd and use shell=True
        args, kwargs = mock_run.call_args
        cmd = args[0]
        self.assertIn("gemini", cmd[0].lower())
        self.assertIn("-y", cmd)
        self.assertIn("-p", cmd)
        self.assertIn(prompt, cmd)

if __name__ == "__main__":
    unittest.main()
