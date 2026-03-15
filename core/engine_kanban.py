import urllib.request
import urllib.parse
import json
import sys
import os
import re
import engine_events
import utils_ui

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "orchestrator_config.json")
TEMPLATE_FILE = os.path.join(os.path.dirname(__file__), "orchestrator_config.template.json")

def _get_config_file():
    if not os.path.exists(CONFIG_FILE) and os.path.exists(TEMPLATE_FILE):
        import shutil
        shutil.copy(TEMPLATE_FILE, CONFIG_FILE)
    return CONFIG_FILE

def load_config():
    data = utils_ui.load_full_config()
    return data.get("kanban", {})

def save_config(updates):
    data = utils_ui.load_full_config()
    data.setdefault("kanban", {}).update(updates)
    utils_ui.save_full_config(data)



def get_base_url():
    cfg = load_config()
    return f"http://{cfg['ip']}:{cfg['port']}/api"

def api_request(path, method='GET', data=None):
    cfg = load_config()
    url = f"{get_base_url()}/{path.lstrip('/')}"
    encoded_data = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=encoded_data, method=method)
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req) as response:
            if response.status in [200, 201]:
                res_data = json.loads(response.read())
                if res_data.get("success"): return res_data.get("data")
    except: pass
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
    res = api_request(f"tasks/{task_id}", method='PUT', data=updates)
    if res: engine_events.emit("task_updated", {"id": task_id, "updates": updates})
    return res

def extract_recipient(text):
    if not text: return None
    match = re.search(r"(?:^[-*]\s*)?Rec[ei]pient:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else None

def format_task(task, mode="medium", highlight_user=None):
    cfg = load_config()
    colors = cfg.get('colors', {})
    desc = task.get('description', '')
    recipient = extract_recipient(desc)
    status = task.get('status', 'unknown')
    tid = task.get('id', 'N/A')
    title = task.get('title', 'No Title')
    
    is_for_me = highlight_user and recipient and highlight_user.lower() in recipient.lower()
    color = colors.get('green', '') if is_for_me else ""
    reset = colors.get('reset', '') if is_for_me else ""

    if mode == "minimal":
        recipient_str = f" | Recipient: {recipient}" if recipient else ""
        return f"{color}- {title} ({tid}) [{status}]{recipient_str}{reset}"
    
    lines = [f"{color}Task:            [{status}] {title} ({tid}){reset}"]
    lines.append(f"Created/Updated: {task.get('created_at')} / {task.get('updated_at')}")
    lines.append(f"Recipient:       {color}{recipient}{reset}" if recipient else f"Recipient:       None")
    if mode == "full" and desc: lines.append(f"Desc:\n{desc}")
    return "\n".join(lines)
