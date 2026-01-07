import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json
import io

# Add tools/kanban to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tools', 'kanban'))
import client

class TestKanbanClient(unittest.TestCase):

    def setUp(self):
        # Ensure a mock config exists for tests
        self.mock_config = {
            "ip": "127.0.0.1",
            "port": "8080",
            "last_project": "testProj",
            "last_user": "testUser",
            "poll_interval": 1.0,
            "colors": {
                "red": "", "green": "", "yellow": "", "reset": ""
            }
        }
        self.config_patcher = patch('client.load_config', return_value=self.mock_config)
        self.config_patcher.start()

    def tearDown(self):
        self.config_patcher.stop()

    @patch('urllib.request.urlopen')
    def test_list_projects_success(self, mock_urlopen):
        # Mock API response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_data = {
            "success": True,
            "data": [
                {"name": "proj1", "id": "uuid1"},
                {"name": "proj2", "id": "uuid2"}
            ]
        }
        mock_response.read.return_value = json.dumps(mock_data).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        projects = client.list_projects()
        self.assertEqual(len(projects), 2)
        self.assertEqual(projects[0]['name'], "proj1")

    def test_extract_recipient(self):
        text = "Some description\n- Recipient: Alice"
        self.assertEqual(client.extract_recipient(text), "Alice")
        
        text2 = "No recipient here"
        self.assertIsNone(client.extract_recipient(text2))
        
        text3 = "Recipient: Bob"
        self.assertEqual(client.extract_recipient(text3), "Bob")

    def test_format_task_minimal(self):
        task = {
            "title": "Fix Bug",
            "id": "123",
            "status": "todo",
            "description": "Recipient: Alice"
        }
        formatted = client.format_task(task, mode="minimal")
        self.assertIn("- Fix Bug (123) [todo] | Recipient: Alice", formatted)

    @patch('client.list_projects')
    @patch('client.save_config')
    def test_resolve_project_id(self, mock_save, mock_list):
        mock_list.return_value = [{"name": "hexArena", "id": "uuid-hex"}]
        
        # Test by name
        pid = client.resolve_project_id("hexArena")
        self.assertEqual(pid, "uuid-hex")
        mock_save.assert_called_with({"last_project": "hexArena"})

        # Test by ID (not in list)
        pid2 = client.resolve_project_id("some-other-id")
        self.assertEqual(pid2, "some-other-id")

if __name__ == '__main__':
    unittest.main()
