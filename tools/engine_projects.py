import os
import json
import subprocess
import engine_events

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "orchestrator_config.json")
AGENT_DEFS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agent_definitions")

def _git_cmd(path, args):
    """Internal helper for git commands."""
    return subprocess.check_output(["git", "-C", path] + args, stderr=subprocess.STDOUT, text=True).strip()

def load_projects():
    if not os.path.exists(CONFIG_FILE): return []
    with open(CONFIG_FILE, 'r') as f: return json.load(f).get("projects", [])

def save_projects(projects):
    if not os.path.exists(CONFIG_FILE): return
    with open(CONFIG_FILE, 'r') as f: full_cfg = json.load(f)
    full_cfg["projects"] = projects
    with open(CONFIG_FILE, 'w') as f: json.dump(full_cfg, f, indent=4)

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

    role_file = os.path.join(AGENT_DEFS_DIR, f"{role}.md")

    

    # Try to find absolute path of 'gemini' to avoid 'File not found' in shells

    gemini_path = "gemini"

    try:

        gemini_path = subprocess.check_output(["where", "gemini"], text=True).strip().splitlines()[0]

    except:

        pass



    cmd = f'"{gemini_path}" --prompt "{role_file}"'

    try:

        # If gemini is a batch file or needs a shell, cmd /k handles it.

        # However, nested quotes in 'cmd /k "..."' can be tricky.

        # Windows Terminal (wt) handles arguments as separate strings if provided as a list.

        subprocess.Popen(["wt", "-d", path, "new-tab", "--title", title, "cmd", "/k", cmd])

    except:

        subprocess.Popen(f"start \"{title}\" /D \"{path}\" cmd /k \"{cmd}\"", shell=True)

    engine_events.emit("worker_launched", {"title": title, "project": project, "role": role})

    return title
