import threading
import time
import os
import re
import engine_pty
import engine_projects
import terminal_emulator

class WorkerManagerPTY:
    def __init__(self, full_config):
        self.full_config = full_config
        self.workers = [] # List of dicts
        self.status_lock = threading.Lock()
        self.on_update_callback = None
        self.on_buffer_callback = None # (worker_id, full_text)

    def spawn_worker(self, project, role):
        title = f"{project['name']}_{role}"
        path = project['local_path']
        
        # Grid dimensions should ideally match UI
        cols = self.full_config.get("terminal", {}).get("cols", 120)
        rows = self.full_config.get("terminal", {}).get("rows", 30)
        
        pty = engine_pty.PTY(cols=cols, rows=rows)
        screen = terminal_emulator.TerminalScreen(cols=cols, rows=rows)
        
        worker_id = f"PTY:{int(time.time())}"
        worker = {
            "id": worker_id,
            "terminal": title,
            "role": role,
            "folder": project['name'],
            "path": path,
            "pty": pty,
            "screen": screen,
            "status": "Starting",
            "start_time": time.time(),
            "last_buffer": ""
        }
        
        def handle_output(text):
            with self.status_lock:
                screen.feed(text)
                full_view = screen.get_text()
                worker["last_buffer"] = full_view
            
            if self.on_buffer_callback:
                self.on_buffer_callback(worker_id, full_view)

        pty.on_output = handle_output
        
        # Use powershell as default shell
        cmd = f"powershell.exe -NoLogo -NoExit -Command \"cd '{path}'; Clear-Host; Write-Host '--- Internal Interactive Worker Started: {role} ---'\""
        
        try:
            pid = pty.spawn(cmd, cwd=path)
            worker["pid"] = pid
            worker["status"] = "Online"
        except Exception as e:
            worker["status"] = f"Error: {e}"
            print(f"[WorkerManagerPTY] Spawn Error: {e}")

        with self.status_lock:
            self.workers.append(worker)
        
        if self.on_update_callback:
            self.on_update_callback()
            
        return worker_id

    def kill_worker(self, worker_id):
        with self.status_lock:
            for i, w in enumerate(self.workers):
                if w["id"] == worker_id:
                    w["pty"].close()
                    self.workers.pop(i)
                    break
        if self.on_update_callback:
            self.on_update_callback()

    def send_to_worker(self, worker_id, text):
        with self.status_lock:
            for w in self.workers:
                if w["id"] == worker_id:
                    w["pty"].write(text)
                    return True
        return False

    def get_workers(self):
        with self.status_lock:
            worker_list = []
            status_list = []
            for w in self.workers:
                elapsed = int(time.time() - w['start_time'])
                mins, secs = divmod(elapsed, 60)
                status_list.append(f"{mins}m {secs}s")
                
                worker_list.append({
                    "id": w["id"],
                    "terminal": w["terminal"],
                    "status": w["status"],
                    "role": w["role"],
                    "folder": w["folder"],
                    "size": len(w["last_buffer"]),
                    "last_buffer": w["last_buffer"]
                })
            return worker_list, status_list

    def stop_all(self):
        with self.status_lock:
            for w in self.workers:
                w["pty"].close()
            self.workers = []