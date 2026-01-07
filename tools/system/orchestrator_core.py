import win32gui
import win32con
import pyautogui
import subprocess
import os
import tempfile
import threading
import time
import json
from terminal_core import TerminalCore

PROJECTS_FILE = os.path.join(os.path.dirname(__file__), "projects.json")
AGENT_DEFS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "agent_definitions")

class OrchestratorCore(TerminalCore):
    def __init__(self):
        super().__init__()
        self.projects = self.load_projects()

    def load_projects(self):
        if os.path.exists(PROJECTS_FILE):
            try:
                with open(PROJECTS_FILE, 'r') as f:
                    return json.load(f)
            except: pass
        return []

    def save_projects(self):
        try:
            with open(PROJECTS_FILE, 'w') as f:
                json.dump(self.projects, f, indent=4)
        except Exception as e:
            print(f"Error saving projects: {e}")

    def add_project(self, name, local_path, kanban_project_name):
        project = {
            "name": name,
            "local_path": local_path,
            "kanban_project_name": kanban_project_name
        }
        self.projects.append(project)
        self.save_projects()
        return project

    def delete_project(self, name):
        self.projects = [p for p in self.projects if p['name'] != name]
        self.save_projects()

    def update_project(self, old_name, new_data):
        for p in self.projects:
            if p['name'] == old_name:
                p.update(new_data)
                break
        self.save_projects()

    def get_git_info(self, path):
        if not os.path.exists(path):
            return "Path not found", ""
        try:
            # Check if git repo
            is_git = subprocess.check_output(["git", "-C", path, "rev-parse", "--is-inside-work-tree"], 
                                             stderr=subprocess.STDOUT, text=True).strip() == "true"
            if not is_git:
                return "Not a Git repo", ""
            
            branch = subprocess.check_output(["git", "-C", path, "branch", "--show-current"], 
                                             stderr=subprocess.STDOUT, text=True).strip()
            # Basic status
            status = subprocess.check_output(["git", "-C", path, "status", "--short"], 
                                             stderr=subprocess.STDOUT, text=True).strip()
            status_summary = "Clean" if not status else "Modified"
            return branch, status_summary
        except Exception as e:
            return f"Git Error: {str(e)[:20]}", ""

    def get_roles(self):
        if not os.path.exists(AGENT_DEFS_DIR):
            return []
        return [f.replace(".md", "") for f in os.listdir(AGENT_DEFS_DIR) if f.endswith(".md")]

    def launch_worker(self, project, role):
        """
        Launches an external terminal window with gemini cli.
        Returns the title of the window to search for.
        """
        title = f"Agent_{project['name']}_{role}"
        path = project['local_path']
        role_file = os.path.join(AGENT_DEFS_DIR, f"{role}.md")
        
        # Command to launch: wt (Windows Terminal) if available, else cmd
        # We use 'gemini' assuming it's in path.
        cmd = f'gemini --prompt "{role_file}"'
        
        try:
            # Try launching with Windows Terminal first for specific title support
            # wt -d [path] --title [title] cmd /k [cmd]
            subprocess.Popen(["wt", "-d", path, "new-tab", "--title", title, "cmd", "/k", cmd])
        except FileNotFoundError:
            # Fallback to standard CMD: start "[title]" /D "[path]" cmd /k "[cmd]"
            subprocess.Popen(f"start \"{title}\" /D \"{path}\" cmd /k \"{cmd}\"", shell=True)
            
        return title
