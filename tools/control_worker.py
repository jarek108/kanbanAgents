"""
Worker Dispatcher Script.
Triggers a 'start' signal when a specific worker is assigned to tasks.
"""
import sys
import time
import argparse
import get_tasks
import urllib.request
import json

DEFAULT_INTERVAL = 1
DEFAULT_URL = "http://192.168.1.185:61154"
DEFAULT_PROJECT = "hexArena"

def close_task(task_id, base_url):
    """
    Moves a task to 'done' status via the API.
    """
    url = f"{base_url}/tasks/{task_id}"
    data = json.dumps({"status": "done"}).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, method='PUT')
    req.add_header('Content-Type', 'application/json')
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print(f"  [SUCCESS] Task {task_id} moved to 'done'.")
            else:
                print(f"  [ERROR] Failed to close task {task_id}: HTTP {response.status}")
    except Exception as e:
        print(f"  [ERROR] Exception while closing task {task_id}: {e}")

def get_worker_tasks(project_id, base_url, worker_name):
    """
    Fetches all tasks for a project and filters for those assigned to worker_name.
    Returns a dictionary of {task_id: task_title}.
    """
    tasks = get_tasks.fetch_tasks(project_id, base_url)
    if tasks is None:
        return {}
        
    worker_tasks = {}
    for task in tasks:
        recipient = get_tasks.extract_recipient(task.get('description', ''))
        # Only include if recipient matches AND task is 'inprogress'
        if recipient and worker_name.lower() in recipient.lower():
            if task.get('status') == 'inprogress':
                worker_tasks[task['id']] = task['title']
    return worker_tasks

def stub_worker(task_ids, worker_name, project_id, base_url):
    """
    A stub worker that processes and moves tasks to 'done'.
    """
    for tid in task_ids:
        print(f"DEBUG: Stub worker for {worker_name} is closing task {tid}...")
        close_task(tid, base_url)

def run_control_worker(worker_name, project_name, interval, api_url, debug=False):
    """
    Monitors the project and prints a start message for newly assigned tasks.
    """
    base_url = f"{api_url}/api" if not api_url.endswith("/api") else api_url
    project_id = get_tasks.get_project_id(project_name, base_url)
    
    if not project_id:
        # Fallback: try as ID
        project_id = project_name
        
    print(f"Control Worker active for '{worker_name}' on project '{project_name}' (Debug: {debug})...")
    
    # Initial Scan
    known_assignments = get_worker_tasks(project_id, base_url, worker_name)
    if known_assignments:
        titles = "\n\t".join(known_assignments.values())
        print(f"start a {worker_name} for tasks:\n\t{titles}")
        if debug:
            stub_worker(known_assignments.keys(), worker_name, project_id, base_url)
    
    known_ids = set(known_assignments.keys())
    
    try:
        while True:
            time.sleep(interval)
            
            current_assignments = get_worker_tasks(project_id, base_url, worker_name)
            current_ids = set(current_assignments.keys())
            
            # Identify new arrivals
            new_ids = current_ids - known_ids
            
            if new_ids:
                new_titles = [current_assignments[tid] for tid in new_ids]
                titles_str = "\n\t".join(new_titles)
                print(f"start a {worker_name} for tasks:\n\t{titles_str}")
                if debug:
                    stub_worker(new_ids, worker_name, project_id, base_url)
                
            # Update state (we only care about new additions for the 'start' trigger)
            known_ids = current_ids
            
    except KeyboardInterrupt:
        print("\nControl Worker stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trigger worker starts based on Kanban assignments.")
    parser.add_argument("worker_name", help="Name of the worker to monitor")
    parser.add_argument("--project", default=DEFAULT_PROJECT, help=f"Project name or ID (default: {DEFAULT_PROJECT})")
    parser.add_argument("--interval", "-i", type=float, default=DEFAULT_INTERVAL, help=f"Poll interval (default: {DEFAULT_INTERVAL}s)")
    parser.add_argument("--url", "-u", default=DEFAULT_URL, help=f"API Base URL (default: {DEFAULT_URL})")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode and run stub worker")
    
    args = parser.parse_args()
    
    run_control_worker(args.worker_name, args.project, args.interval, args.url, args.debug)
