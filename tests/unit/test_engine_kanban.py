import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Add tools to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tools'))
import engine_kanban

class TestEngineKanban(unittest.TestCase):

    def setUp(self):
        self.mock_config = {
            "ip": "127.0.0.1",
            "port": "8080",
            "last_project": "testProj",
            "last_user": "testUser",
            "poll_interval": 1.0,
            "colors": {"red": "", "green": "", "yellow": "", "reset": ""}
        }
        self.config_patcher = patch('engine_kanban.load_config', return_value=self.mock_config)
        self.config_patcher.start()

    def tearDown(self):
        self.config_patcher.stop()

    @patch('urllib.request.urlopen')
    def test_list_projects_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_data = {"success": True, "data": [{"name": "proj1", "id": "uuid1"}]}
        mock_response.read.return_value = json.dumps(mock_data).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        projects = engine_kanban.list_projects()
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]['name'], "proj1")

    def test_extract_recipient(self):
        self.assertEqual(engine_kanban.extract_recipient("Recipient: Alice"), "Alice")

if __name__ == '__main__':
    unittest.main()