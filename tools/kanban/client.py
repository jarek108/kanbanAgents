"""
Unified Kanban API Client.
Handles project management, task tracking, and configuration persistence.

Usage Examples:
    python tools/kanban/client.py list-projects
    python tools/kanban/client.py get-tasks hexArena
    python tools/kanban/client.py get-tasks --recipient Manager --minimal
    python tools/kanban/client.py update-task [UUID] --status inprogress
    python tools/kanban/client.py update-task [UUID] --recipient "Coder-ID"
    python tools/kanban/client.py --ip 192.168.1.185 --port 61154 list-projects
"""
import urllib.request
import urllib.parse
import json
import sys
import argparse
import re
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"CRITICAL ERROR: Configuration file '{CONFIG_FILE}' missing.")
        sys.exit(1)
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to parse config: {e}")
        sys.exit(1)

def save_config(updates):
    config = load_config()
    config.update(updates)
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        config = load_config()
        print(f"{config['colors']['red']}Error saving config: {e}{config['colors']['reset']}")

def get_base_url():
    config = load_config()
    return f"http://{config['ip']}:{config['port']}/api"

def api_request(path, method='GET', data=None):
    config = load_config()
    url = f"{get_base_url()}/{path.lstrip('/')}"
    encoded_data = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=encoded_data, method=method)
    req.add_header('Content-Type', 'application/json')
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status in [200, 201]:
                res_data = json.loads(response.read())
                if res_data.get("success"):
                    return res_data.get("data")
                print(f"{config['colors']['red']}API Error: {res_data.get('error')}{config['colors']['reset']}")
            else:
                print(f"{config['colors']['red']}HTTP Error: {response.status}{config['colors']['reset']}")
    except Exception as e:
        print(f"{config['colors']['red']}Connection Error: {e}{config['colors']['reset']}")
    return None

def list_projects():
    return api_request("projects")

def resolve_project_id(project_name_or_id):
    projects = list_projects()
    if not projects: return project_name_or_id
    for p in projects:
        if p['name'] == project_name_or_id or p['id'] == project_name_or_id:
            save_config({"last_project": p['name']})
            return p['id']
    return project_name_or_id

def get_tasks(project_id):
    params = urllib.parse.urlencode({'project_id': project_id})
    return api_request(f"tasks?{params}")

def update_task(task_id, updates):
    return api_request(f"tasks/{task_id}", method='PUT', data=updates)

def extract_recipient(text):
    if not text: return None
    match = re.search(r"(?:^[-*]\s*)?Rec[ei]pient:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else None

def format_task(task, mode="medium", highlight_user=None):
    config = load_config()
    colors = config['colors']
    desc = task.get('description', '')
    recipient = extract_recipient(desc)
    status = task.get('status', 'unknown')
    tid = task.get('id', 'N/A')
    title = task.get('title', 'No Title')
    
    is_for_me = highlight_user and recipient and highlight_user.lower() in recipient.lower()
    color = colors['green'] if is_for_me else ""
    reset = colors['reset'] if is_for_me else ""

    if mode == "minimal":
        recipient_str = f" | Recipient: {recipient}" if recipient else ""
        return f"{color}- {title} ({tid}) [{status}]{recipient_str}{reset}"
    
    lines = [f"{color}Task:            [{status}] {title} ({tid}){reset}"]
    lines.append(f"Created/Updated: {task.get('created_at')} / {task.get('updated_at')}")
    
    recipient_val = f"{color}{recipient}{reset}" if recipient else f"{colors['red']}None{colors['reset']}"
    lines.append(f"Recipient:       {recipient_val}")
    
    if mode == "full" and desc:
        lines.append(f"Desc:\n{desc}")
    return "\n".join(lines)

def main():
    config = load_config()
    parser = argparse.ArgumentParser(description="Kanban API Unified Client")
    parser.add_argument("--ip", help=f"Set API IP (Last: {config['ip']})")
    parser.add_argument("--port", help=f"Set API Port (Last: {config['port']})")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    subparsers.add_parser("list-projects", help="List all available projects")

    get_parser = subparsers.add_parser("get-tasks", help="Get tasks for a project")
    get_parser.add_argument("project", default=config['last_project'], nargs="?", help="Project name or ID")
    get_parser.add_argument("--recipient", help="Filter by recipient name")
    get_parser.add_argument("--status", help="Filter by status")
    get_parser.add_argument("--minimal", action="store_true", help="One-line format")
    get_parser.add_argument("--full", action="store_true", help="Include descriptions")

    up_parser = subparsers.add_parser("update-task", help="Update a task")
    up_parser.add_argument("task_id", help="UUID of the task")
    up_parser.add_argument("--status", help="New status")
    up_parser.add_argument("--title", help="New title")
    up_parser.add_argument("--description", help="New description")
    up_parser.add_argument("--recipient", help="Set recipient in description")

    args = parser.parse_args()

    # Update IP/Port if provided
    updates = {}
    if args.ip: updates['ip'] = args.ip
    if args.port: updates['port'] = args.port
    if updates: save_config(updates)

    if args.command == "list-projects":
        projects = list_projects()
        if projects:
            print(f"{ 'Name':<20} | {'ID'}")
            print("-" * 60)
            for p in projects:
                print(f"{p['name']:<20} | {p['id']}")

    elif args.command == "get-tasks":
        pid = resolve_project_id(args.project)
        tasks = get_tasks(pid)
        if tasks:
            mode = "minimal" if args.minimal else ("full" if args.full else "medium")
            for t in tasks:
                rec = extract_recipient(t.get('description', ''))
                if args.recipient and (not rec or args.recipient.lower() not in rec.lower()): continue
                if args.status and t.get('status') != args.status: continue
                print(format_task(t, mode=mode, highlight_user=args.recipient))
                if mode != "minimal": print("-" * 40)

    elif args.command == "update-task":
        up_data = {}
        if args.status: up_data['status'] = args.status
        if args.title: up_data['title'] = args.title
        if args.description: up_data['description'] = args.description
        if args.recipient: up_data['description'] = f"Recipient: {args.recipient}"

        if up_data:
            res = update_task(args.task_id, up_data)
            if res:
                config = load_config()
                print(f"{config['colors']['green']}Task {args.task_id} updated successfully.{config['colors']['reset']}")

if __name__ == "__main__":
    main()
