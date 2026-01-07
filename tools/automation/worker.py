import sys
import os
import time
import argparse
# Add parent and kanban folder to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'kanban'))
import client

def get_worker_tasks(project_id, worker_name):
    tasks = client.get_tasks(project_id)
    if tasks is None: return {}
    worker_tasks = {}
    for task in tasks:
        recipient = client.extract_recipient(task.get('description', ''))
        if recipient and worker_name.lower() in recipient.lower():
            if task.get('status') == 'inprogress':
                worker_tasks[task['id']] = task['title']
    return worker_tasks

def run_control_worker(worker_name, project_name=None, debug=False):
    config = client.load_config()
    project_name = project_name or config['last_project']
    project_id = client.resolve_project_id(project_name)
    interval = config['poll_interval']
    
    print(f"Control Worker active for '{worker_name}' on project '{project_name}'...")
    
    known_assignments = get_worker_tasks(project_id, worker_name)
    known_ids = set(known_assignments.keys())
    
    try:
        while True:
            time.sleep(interval)
            current_assignments = get_worker_tasks(project_id, worker_name)
            current_ids = set(current_assignments.keys())
            new_ids = current_ids - known_ids
            if new_ids:
                print(f"New tasks for {worker_name}: {[current_assignments[tid] for tid in new_ids]}")
            known_ids = current_ids
    except KeyboardInterrupt:
        print("\nWorker stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kanban Worker.")
    parser.add_argument("worker_name", help="Name of the worker")
    parser.add_argument("--project", help="Project name or ID")
    args = parser.parse_args()
    run_control_worker(args.worker_name, args.project)