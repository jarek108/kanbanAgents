"""
Task management utilities for fetching, filtering, and formatting Kanban tasks.
Supports multiple presentation modes (minimal, medium, full) and recipient filtering.
"""
import urllib.request
import json
import sys
import urllib.parse
import re

# ANSI Color codes
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

DEFAULT_BASE_URL = "http://192.168.1.185:61154/api"
DEFAULT_PROJECT = "hexArena"
DEFAULT_RECIPIENT = "ALL"

def extract_recipient(text):
    """
    Extracts the recipient name from a task description using regex.
    Supports 'Recipient:' or 'Recepient:' with optional leading markers.
    """
    if not text:
        return None
    # Match "- Recipient/Recepient: ..." or "Recipient/Recepient: ..."
    match = re.search(r"(?:^[-*]\s*)?Rec[ei]pient:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def format_task(task, mode="medium", highlight_user=None):
    """
    Formats a task object into a string for terminal display.
    
    Args:
        task (dict): The task data from the API.
        mode (str): 'minimal', 'medium', or 'full' presentation style.
        highlight_user (str): Optional user ID to highlight if they are the recipient.
    """
    desc = task.get('description', '')
    recipient = extract_recipient(desc)
    
    is_for_me = False
    if highlight_user and recipient and highlight_user.lower() in recipient.lower():
        is_for_me = True

    lines = []
    if mode == "minimal":
        recipient_str = f" | Recipient: {recipient}" if recipient else ""
        msg = f"- {task.get('title')} ({task.get('id')}) [{task.get('status')}]{recipient_str}"
        if is_for_me:
            lines.append(f"{GREEN}{msg} [ASSIGNED TO YOU]{RESET}")
        else:
            lines.append(msg)
    
    else:
        # Medium and Full both share the header info
        task_line = f"Task:            [{task.get('status')}] {task.get('title')} ({task.get('id')})"
        if is_for_me:
            lines.append(f"{GREEN}{task_line} [ASSIGNED TO YOU]{RESET}")
        else:
            lines.append(task_line)
            
        created = task.get('created_at', 'N/A')
        updated = task.get('updated_at', 'N/A')
        date_str = created if created == updated else f"{created} / {updated}"
        lines.append(f"Created/Updated: {date_str}")
        
        if recipient:
            if is_for_me:
                lines.append(f"Recipient:       {GREEN}{recipient}{RESET}")
            else:
                lines.append(f"Recipient:       {recipient}")
        else:
            lines.append(f"Recipient:       {RED}None{RESET}")
            
        if mode == "full" and desc:
            lines.append(f"Desc:    {desc}")
            
    return "\n".join(lines)

def get_project_id(project_name, base_url=DEFAULT_BASE_URL):
    """Resolves a project name to its UUID project_id."""
    url = f"{base_url}/projects"
    try:
        with urllib.request.urlopen(url) as response:
            if response.status != 200:
                print(f"Error fetching projects: HTTP {response.status}")
                return None
            
            data = json.loads(response.read())
            if not data.get("success"):
                print(f"Error: {data.get('error')}")
                return None
                
            for project in data.get("data", []):
                if project.get("name") == project_name:
                    return project.get("id")
            
            print(f"Project '{project_name}' not found.")
            return None
            
    except Exception as e:
        print(f"Error resolving project ID: {e}")
        return None

def fetch_tasks(project_id, base_url=DEFAULT_BASE_URL):
    """Fetches all tasks for a given project UUID."""
    params = urllib.parse.urlencode({'project_id': project_id})
    url = f"{base_url}/tasks?{params}"
    
    try:
        with urllib.request.urlopen(url) as response:
            if response.status != 200:
                print(f"Error fetching tasks: HTTP {response.status}")
                return None
            
            data = json.loads(response.read())
            if not data.get("success"):
                print(f"Error: {data.get('error')}")
                return None
                
            return data.get("data", [])

    except Exception as e:
        print(f"Error fetching tasks: {e}")
        return None

def list_tasks(project_id, base_url=DEFAULT_BASE_URL, presentation_mode="medium", recipient_filter="ALL"):
    """
    Prints a filtered and formatted list of tasks to the console.
    """
    tasks = fetch_tasks(project_id, base_url)
    if tasks is None:
        return

    if not tasks:
        print("No tasks found.")
        return

    filter_desc = f" (Filter: {recipient_filter})" if recipient_filter != "ALL" else ""
    print(f"Tasks for Project ID {project_id}{filter_desc}:")
    print("-" * 80)
    for task in tasks:
        desc = task.get('description', '')
        recipient = extract_recipient(desc)
        
        # Apply filter
        if recipient_filter != "ALL":
            if not recipient or recipient_filter.lower() not in recipient.lower():
                continue
        
        print(format_task(task, presentation_mode, highlight_user=None if recipient_filter == "ALL" else recipient_filter))
        if presentation_mode != "minimal":
            print("-" * 40)
    
    if presentation_mode == "minimal":
        print("-" * 80)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch and list tasks for a Kanban project.")
    parser.add_argument("project", nargs="?", default=DEFAULT_PROJECT, help=f"Name or ID of the project (default: {DEFAULT_PROJECT})")
    parser.add_argument("--minimal", action="store_true", help="Show minimal one-line summary")
    parser.add_argument("--full-presentation", action="store_true", help="Show full task details including description")
    parser.add_argument("--recipient", default=DEFAULT_RECIPIENT, help=f"Filter tasks by recipient (default: {DEFAULT_RECIPIENT})")
    
    args = parser.parse_args()
    target = args.project
    
    mode = "medium"
    if args.minimal:
        mode = "minimal"
    elif args.full_presentation:
        mode = "full"
    
    # Logic: Resolve name to ID first.
    pid = get_project_id(target)
    
    if pid:
        list_tasks(pid, presentation_mode=mode, recipient_filter=args.recipient)
    else:
        # If not found by name, maybe the user provided an ID directly?
        # We can try to list tasks with it directly.
        print(f"Could not find project named '{target}'. Assuming it might be an ID...")
        list_tasks(target, presentation_mode=mode, recipient_filter=args.recipient)
