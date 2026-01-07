"""
CLI tool to list all available projects from the Kanban API.
"""
import urllib.request
import json
import sys

URL = "http://192.168.1.185:61154/api/projects"

def list_projects():
    """
    Fetches the list of projects from the API and prints their names and IDs.
    """
    try:
        with urllib.request.urlopen(URL) as response:
            if response.status != 200:
                print(f"Error: Server returned status {response.status}")
                sys.exit(1)
            
            data = response.read()
            json_data = json.loads(data)
            
            if not json_data.get("success"):
                print(f"Error: API reported failure: {json_data.get('error')}")
                sys.exit(1)
                
            projects = json_data.get("data", [])
            
            if not projects:
                print("No projects found.")
                return

            print(f"Found {len(projects)} projects:")
            print("-" * 30)
            for project in projects:
                name = project.get("name", "Unknown")
                pid = project.get("id", "Unknown")
                print(f"Name: {name}")
                print(f"ID:   {pid}")
                print("-" * 30)

    except urllib.error.URLError as e:
        print(f"Error connecting to {URL}: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    list_projects()
