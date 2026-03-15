import threading
import time
import os
import engine_projects
import engine_kanban

class ProjectManager:
    def __init__(self, full_config):
        self.full_config = full_config
        self.project_status_cache = {} # name -> git_info_dict
        self.is_running = True
        self.status_lock = threading.Lock()
        self.on_update_callback = None

    def start(self):
        threading.Thread(target=self._background_status_loop, daemon=True).start()

    def stop(self):
        self.is_running = False

    def get_cache(self):
        with self.status_lock:
            return dict(self.project_status_cache)

    def _background_status_loop(self):
        """Heavy lifting (Git/API) happens here in a separate thread."""
        while self.is_running:
            try:
                # 1. Update Project Statuses
                projects = engine_projects.load_projects()
                new_project_cache = {}
                for p in projects:
                    git_info = engine_projects.get_git_info(p['local_path'])
                    kb_url = engine_projects.get_kanban_url(p['kanban_project_name'])
                    new_project_cache[p['name']] = {
                        "git": git_info, # (branch, status, root, commit, remote)
                        "kanban_url": kb_url,
                        "data": p
                    }

                # 2. Commit to cache
                with self.status_lock:
                    self.project_status_cache = new_project_cache
                
                if self.on_update_callback:
                    self.on_update_callback()
                    
            except Exception as e:
                print(f"[ProjectManager Error] {e}")

            # Sleep based on config
            ms = self.full_config.get("terminal", {}).get("git_refresh_ms", 3000)
            time.sleep(ms / 1000.0)
