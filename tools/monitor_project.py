"""
Real-time Kanban project monitoring tool.
Polls the API for changes and displays diffs for task updates.
Highlights assignments for a specific target user.
"""
import sys
import time
import argparse
import get_tasks
import difflib
import re

DEFAULT_INTERVAL = 1
DEFAULT_URL = "http://192.168.1.185:61154"
DEFAULT_PROJECT = "hexArena"
DEFAULT_USER = "Manager"

# ANSI Color codes
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def extract_recipient(text):
    """Extracts recipient from text. Proxy for get_tasks.extract_recipient."""
    return get_tasks.extract_recipient(text)

def get_color_diff(old_text, new_text):
    """Generates a color-coded unified diff between two strings."""
    old_lines = (old_text or "").splitlines()
    new_lines = (new_text or "").splitlines()
    
    # Generate unified diff, skipping the header lines (---, +++, @@)
    diff = difflib.unified_diff(old_lines, new_lines, lineterm='')
    colored_diff = []
    for line in diff:
        if line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
            continue
        if line.startswith('-'):
            colored_diff.append(f"{RED}{line}{RESET}")
        elif line.startswith('+'):
            colored_diff.append(f"{GREEN}{line}{RESET}")
        else:
            colored_diff.append(line)
    return colored_diff

def monitor_project(project_name, sampling_interval=DEFAULT_INTERVAL, api_url=DEFAULT_URL, run_once=False, target_user=DEFAULT_USER):
    """
    Main loop that polls the API for project task changes.
    
    Args:
        project_name (str): Name or UUID of project.
        sampling_interval (float): Seconds between polls.
        api_url (str): Base URL of the API.
        run_once (bool): If True, exits after one cycle.
        target_user (str): User ID to highlight for assignments.
    """
    interval = sampling_interval
    print(f"Monitoring project '{project_name}' for user '{target_user}' every {interval} seconds at {api_url}...")
    
    # Resolve project ID
    base_url = f"{api_url}/api" if not api_url.endswith("/api") else api_url
    project_id = get_tasks.get_project_id(project_name, base_url)
    
    if not project_id:
        # Fallback: maybe it's an ID
        project_id = project_name
        print(f"Assuming '{project_name}' is a Project ID.")

    # Initial fetch
    previous_tasks_map = {}
    initial_tasks = get_tasks.fetch_tasks(project_id, base_url)
    
    if initial_tasks is None:
        print("Failed to fetch initial tasks. Exiting.")
        return

    print(f"Initial load: {len(initial_tasks)} tasks found.")
    
    # Sort initial tasks so user's tasks are first
    def is_for_user(t):
        r = extract_recipient(t.get('description', ''))
        return target_user and r and target_user.lower() in r.lower()
    
    sorted_tasks = sorted(initial_tasks, key=lambda t: not is_for_user(t))

    for task in sorted_tasks:
        previous_tasks_map[task['id']] = task
        print(get_tasks.format_task(task, mode="medium", highlight_user=target_user))
        print("-" * 40)
    
    try:
        while True:
            time.sleep(interval)
            
            current_tasks = get_tasks.fetch_tasks(project_id, base_url)
            if current_tasks is None:
                print("Error fetching tasks, skipping this cycle.")
                continue
                
            current_tasks_map = {task['id']: task for task in current_tasks}
            
            # Check for new or modified tasks
            for task_id, task in current_tasks_map.items():
                description = task.get('description', '')
                recipient = extract_recipient(description)
                is_for_me = target_user and recipient and target_user.lower() in recipient.lower()

                if task_id not in previous_tasks_map:
                    print(f"\n{GREEN}[NEW]{RESET}")
                    if is_for_me:
                        print(f"      {GREEN}[ACTION REQUIRED] You are the recipient!{RESET}")
                    print(get_tasks.format_task(task, mode="medium", highlight_user=target_user))
                else:
                    prev_task = previous_tasks_map[task_id]
                    prev_recipient = extract_recipient(prev_task.get('description', ''))
                    
                    # Check for changes
                    changes = []
                    if task['title'] != prev_task['title']:
                        changes.append(f"Title: '{prev_task['title']}' -> '{task['title']}'")
                    if task['status'] != prev_task['status']:
                        changes.append(f"Status: '{prev_task['status']}' -> '{task['status']}'")
                    
                    if recipient != prev_recipient:
                        changes.append(f"Recipient: '{prev_recipient}' -> '{recipient}'")

                    if task.get('description') != prev_task.get('description'):
                        old_desc = prev_task.get('description', '')
                        new_desc = task.get('description', '')
                        diff_lines = get_color_diff(old_desc, new_desc)
                        if diff_lines:
                            changes.append("Description changed:")
                            for line in diff_lines:
                                changes.append(f"  {line}")
                        
                    if changes:
                        print(f"\n{YELLOW}[UPDATE]{RESET} Task: {task['title']} (ID: {task_id})")
                        if is_for_me and (recipient != prev_recipient or not prev_recipient):
                            print(f"         {GREEN}[ACTION REQUIRED] You have been marked as the recipient!{RESET}")
                        elif is_for_me:
                            print(f"         {GREEN}[RELEVANT] Update to a task you are assigned to.{RESET}")
                        
                        for change in changes:
                            print(f"         {change}")
            
            # Check for deleted tasks
            for task_id, task in previous_tasks_map.items():
                if task_id not in current_tasks_map:
                    print(f"\n[DELETED] Task deleted: {task['title']} (ID: {task_id})")
            
            # Update state
            previous_tasks_map = current_tasks_map
            
            if run_once:
                break

    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor a Kanban project for changes.")
    parser.add_argument("project_name", nargs="?", default=DEFAULT_PROJECT, help=f"Name or ID of the project to monitor (default: {DEFAULT_PROJECT})")
    parser.add_argument("--interval", "-i", type=float, default=DEFAULT_INTERVAL, help=f"Check interval in seconds (default: {DEFAULT_INTERVAL})")
    parser.add_argument("--url", "-u", default=DEFAULT_URL, help=f"Base URL of the Kanban API (default: {DEFAULT_URL})")
    parser.add_argument("--user", default=DEFAULT_USER, help=f"User ID to monitor for assignments (default: {DEFAULT_USER})")
    parser.add_argument("--run-once", action="store_true", help="Run only one cycle and exit (for testing)")
    
    args = parser.parse_args()
    
    monitor_project(args.project_name, args.interval, args.url, args.run_once, args.user)
