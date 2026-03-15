import unittest
import sys
import os
import shutil
import tempfile
from pathlib import Path

# Add core to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from core import headless_gemini

class TestHeadlessGeminiIntegration(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.workspace = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @unittest.skipIf(shutil.which("gemini") is None and not (Path(os.environ.get("APPDATA", "")) / "npm" / "gemini.cmd").exists(), 
                     "Gemini CLI not found in PATH or APPDATA")
    def test_simple_question_integration(self):
        """
        Integration test to verify that headless_gemini can actually invoke the 
        real Gemini CLI and capture a correct response.
        """
        prompt = "how many states are in the usa, just give a number no words or other remarks or you break the system"
        
        print(f"\n[Test] Sending prompt: {prompt}")
        success, stdout, stderr = headless_gemini.invoke_agent(
            workspace_path=self.workspace,
            prompt=prompt,
            model="gemini-3-flash-preview",
            timeout=60 # Should be fast for a simple question
        )
        
        print(f"[Test] Success: {success}")
        print(f"[Test] STDOUT: '{stdout.strip()}'")
        
        self.assertTrue(success, f"Agent execution failed with stderr: {stderr}")
        self.assertIn("50", stdout.strip(), f"Expected '50' in response, but got: '{stdout}'")

if __name__ == "__main__":
    unittest.main()
