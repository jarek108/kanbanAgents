"""
CLI tool to manually change the status of a Kanban task.
"""
import urllib.request
import json
import sys
import argparse
import get_tasks

def change_status(task_id, new_status, base_url=get_tasks.DEFAULT_BASE_URL):
    """
    Sends a PATCH request to the API to update the task status.
    """
    url = f"{base_url}/tasks/{task_id}"
    data = json.dumps({"status": new_status}).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, method='PUT')
    req.add_header('Content-Type', 'application/json')
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print(f"Successfully updated task {task_id} to status: {new_status}")
            else:
                print(f"Error: Failed to update task. Server returned HTTP {response.status}")
                sys.exit(1)
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        # Try to read the error body for more details
        try:
            error_data = json.loads(e.read())
            print(f"API Error: {error_data.get('error', 'Unknown error')}")
        except:
            pass
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Change the status of a Kanban task.")
    parser.add_argument("task_id", help="The UUID of the task to update")
    parser.add_argument("status", help="The new status (e.g., todo, inprogress, done)")
    parser.add_argument("--url", default=get_tasks.DEFAULT_BASE_URL, help=f"API Base URL (default: {get_tasks.DEFAULT_BASE_URL})")
    
    args = parser.parse_args()
    
    change_status(args.task_id, args.status, args.url)
