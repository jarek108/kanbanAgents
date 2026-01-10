import os
import json
import subprocess
import time
import engine_events
import tempfile
import utils_ui

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "orchestrator_config.json")
AGENT_DEFS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agent_definitions")

def _git_cmd(path, args):
    """Internal helper for git commands."""
    return subprocess.check_output(["git", "-C", path] + args, stderr=subprocess.STDOUT, text=True).strip()

def load_projects():
    data = utils_ui.load_full_config()
    return data.get("projects", [])

def save_projects(projects):
    data = utils_ui.load_full_config()
    data["projects"] = projects
    utils_ui.save_full_config(data)



def add_project(name, local_path, kanban_project_name):
    projects = load_projects()
    project = {"name": name, "local_path": local_path, "kanban_project_name": kanban_project_name}
    projects.append(project)
    save_projects(projects)
    engine_events.emit("project_added", project)
    return project

def delete_project(name):
    projects = load_projects()
    projects = [p for p in projects if p['name'] != name]
    save_projects(projects)
    engine_events.emit("project_deleted", name)

def get_kanban_url(project_name):
    """Returns the web URL for a kanban project."""
    import engine_kanban
    cfg = engine_kanban.load_config()
    # Assuming web UI is at same IP/Port
    base = f"http://{cfg['ip']}:{cfg['port']}"
    pid = engine_kanban.resolve_project_id(project_name)
    return f"{base}/projects/{pid}"

def get_git_info(path):
    if not os.path.exists(path): return "Path not found", "", "", "", ""
    try:
        is_git = _git_cmd(path, ["rev-parse", "--is-inside-work-tree"]) == "true"
        if not is_git: return "Not a Git repo", "", "", "", ""
        
        branch = _git_cmd(path, ["branch", "--show-current"])
        root = _git_cmd(path, ["rev-parse", "--show-toplevel"])
        commit = _git_cmd(path, ["rev-parse", "--short", "HEAD"])
        
        remote = ""
        try:
            remote = _git_cmd(path, ["remote", "get-url", "origin"])
            if remote.endswith(".git"): remote = remote[:-4]
        except: pass
        
        status_raw = _git_cmd(path, ["status", "--short"])
        status = "Clean" if not status_raw else "Modified"
        
        return branch, status, root, commit, remote
    except Exception as e:
        return f"Git Error: {str(e)[:15]}", "", "", "", ""

def get_roles():
    if not os.path.exists(AGENT_DEFS_DIR): return []
    return [f.replace(".md", "") for f in os.listdir(AGENT_DEFS_DIR) if f.endswith(".md")]

def launch_worker(project, role):
    title = f"Agent_{project['name']}_{role}"
    path = project['local_path']
    
    # Create a unique log file in the temp directory
    log_file = os.path.join(tempfile.gettempdir(), f"worker_{int(time.time())}_{title}.log")
    
    print(f"[DEBUG] Launching agent terminal with logging: {title} -> {log_file}")
    
    # Use PowerShell's Start-Transcript to record everything.
    # We wrap the command to start the transcript and then drop into a shell.
    # The 'powershell -NoExit' keeps the terminal open.
    cmd_str = f'Start-Transcript -Path "{log_file}" -Append; Write-Host "--- Worker Started: {role} in {project["name"]} ---"; cd "{path}"'
    
    try:
        # Use Windows Terminal (wt.exe) to group agents in a named window "Agents".
        # IMPORTANT: semicolons must be escaped with \; for wt.exe parser
        wt_cmd_str = cmd_str.replace(';', '\;')
        full_cmd = f'wt -w Agents nt --title "{title}" powershell -NoExit -Command "{wt_cmd_str}"'
        print(f"[DEBUG] Executing: {full_cmd}")
        subprocess.Popen(full_cmd, shell=True)
        pid = None 
    except Exception as e:
        print(f"[DEBUG] WT launch failed: {e}")
        # Fallback to standard start if WT fails
        full_cmd = f'start "{title}" powershell -NoExit -Command "{cmd_str}"'
        subprocess.Popen(full_cmd, shell=True)
        pid = None
    
    engine_events.emit("worker_launched", {
        "title": title, 
        "project": project, 
        "role": role, 
        "pid": pid,
        "log_path": log_file
    })
    return title, pid

def kill_process(pid):
    """Forcefully terminates a process by PID."""
    if not pid: return False
    try:
        import subprocess
        # Using taskkill on Windows for reliable tree killing
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
        return True
    except Exception as e:
        print(f"[Error] Failed to kill process {pid}: {e}")
        return False


