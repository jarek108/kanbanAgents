import sys
import os
import time
import argparse
# Add parent and kanban folder to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'kanban'))
import client
import difflib
import re

def get_color_diff(old_text, new_text):
    config = client.load_config()
    colors = config['colors']
    old_lines = (old_text or "").splitlines()
    new_lines = (new_text or "").splitlines()
    diff = difflib.unified_diff(old_lines, new_lines, lineterm='')
    colored_diff = []
    for line in diff:
        if line.startswith('---') or line.startswith('+++') or line.startswith('@@'): continue
        if line.startswith('-'): colored_diff.append(f"{colors['red']}{line}{colors['reset']}")
        elif line.startswith('+'): colored_diff.append(f"{colors['green']}{line}{colors['reset']}")
        else: colored_diff.append(line)
    return colored_diff

def monitor_project(project_name=None, sampling_interval=None, run_once=False, target_user=None):
    config = client.load_config()
    colors = config['colors']
    project_name = project_name or config['last_project']
    target_user = target_user or config['last_user']
    interval = sampling_interval or config['poll_interval']

    print(f"Monitoring project '{project_name}' for user '{target_user}' every {interval}s...")
    
    project_id = client.resolve_project_id(project_name)
    client.save_config({"last_user": target_user})

    previous_tasks_map = {}
    initial_tasks = client.get_tasks(project_id)
    if initial_tasks is None: return

    for task in initial_tasks:
        previous_tasks_map[task['id']] = task
        print(client.format_task(task, mode="medium", highlight_user=target_user))
        print("-" * 40)
    
    try:
        while True:
            time.sleep(interval)
            current_tasks = client.get_tasks(project_id)
            if current_tasks is None: continue
            current_tasks_map = {task['id']: task for task in current_tasks}
            
            for task_id, task in current_tasks_map.items():
                recipient = client.extract_recipient(task.get('description', ''))
                is_for_me = target_user and recipient and target_user.lower() in recipient.lower()

                if task_id not in previous_tasks_map:
                    print(f"\n{colors['green']}[NEW]{colors['reset']}")
                    print(client.format_task(task, mode="medium", highlight_user=target_user))
                else:
                    prev_task = previous_tasks_map[task_id]
                    changes = []
                    if task['status'] != prev_task['status']:
                        changes.append(f"Status: '{prev_task['status']}' -> '{task['status']}'")
                    if task.get('description') != prev_task.get('description'):
                        diff = get_color_diff(prev_task.get('description', ''), task.get('description', ''))
                        if diff:
                            changes.append("Description changed:")
                            for line in diff: changes.append(f"  {line}")
                        
                    if changes:
                        print(f"\n{colors['yellow']}[UPDATE]{colors['reset']} Task: {task['title']} (ID: {task_id})")
                        for change in changes: print(f"         {change}")
            
            previous_tasks_map = current_tasks_map
            if run_once: break
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor a Kanban project.")
    parser.add_argument("project", nargs="?", help="Project name or ID")
    parser.add_argument("--user", help="User to highlight")
    parser.add_argument("--run-once", action="store_true")
    args = parser.parse_args()
    monitor_project(args.project, target_user=args.user, run_once=args.run_once)