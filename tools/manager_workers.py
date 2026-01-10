import threading
import time
import os
import win32gui
import uiautomation as auto
import engine_terminal
import engine_projects

class WorkerManager:
    def __init__(self, full_config, terminal_engine):
        self.full_config = full_config
        self.terminal = terminal_engine
        self.workers = []
        self.worker_status_cache = [] # List of elapsed time strings
        self._node_cache = {} # (hwnd, runtime_id) -> UIA Element
        self.is_syncing = False
        self.status_lock = threading.Lock()
        self.on_update_callback = None
        self.on_buffer_callback = None # (hwnd, rid, content)

    def start_sync(self):
        if not self.is_syncing:
            self.is_syncing = True
            threading.Thread(target=self._uia_sync_loop, daemon=True).start()

    def stop_sync(self):
        self.is_syncing = False

    def add_worker(self, worker_info):
        with self.status_lock:
            self.workers.append(worker_info)

    def remove_worker(self, index):
        with self.status_lock:
            if 0 <= index < len(self.workers):
                w = self.workers.pop(index)
                cache_key = (w.get("hwnd"), w.get("runtime_id"))
                if cache_key in self._node_cache:
                    del self._node_cache[cache_key]
                return w
        return None

    def get_workers(self):
        with self.status_lock:
            return list(self.workers), list(self.worker_status_cache)

    def get_setup(self):
        """Returns a serializable list of worker configurations."""
        with self.status_lock:
            setup = []
            for w in self.workers:
                setup.append({
                    "terminal": w.get("terminal"),
                    "role": w.get("role"),
                    "folder": w.get("folder"),
                    "kanban": w.get("kanban"),
                    "log_path": w.get("log_path"),
                    "start_time": w.get("start_time", time.time())
                })
            return setup

    def apply_setup(self, setup_data):
        """Re-initializes the worker list from a saved setup."""
        if not setup_data or not isinstance(setup_data, list):
            return
        
        with self.status_lock:
            for item in setup_data:
                if not item.get("terminal"): continue
                worker = {
                    "terminal": item["terminal"],
                    "role": item.get("role", "Unknown"),
                    "folder": item.get("folder", "Unknown"),
                    "kanban": item.get("kanban", "Unknown"),
                    "log_path": item.get("log_path"),
                    "start_time": item.get("start_time", time.time()),
                    "status": "Offline",
                    "id": "???"
                }
                self.workers.append(worker)

    def _resolve_worker_identity(self, w, current_window_list, used_rids):
        """Finds HWND and Runtime ID for a worker based on its terminal title.
        Ensures that a Runtime ID is not used by more than one worker.
        """
        # If already resolved and still valid, mark RID as used and return
        if w.get("hwnd") and win32gui.IsWindow(w["hwnd"]):
            used_rids.add(w.get("runtime_id"))
            return False

        for title, hwnd, rid in current_window_list:
            if rid in used_rids:
                continue
            
            if w["terminal"] == title:
                w["hwnd"] = hwnd
                w["runtime_id"] = rid
                # Use the full RID for internal ID to ensure uniqueness
                w["id"] = f"{hwnd}:{rid}"
                used_rids.add(rid)
                return True
        return False

    def _uia_sync_loop(self):
        with auto.UIAutomationInitializerInThread():
            while self.is_syncing:
                with self.status_lock:
                    current_workers = list(self.workers)

                needs_refresh = False
                new_worker_times = []
                cached_window_list = self.terminal.get_window_list()
                
                # Track RIDs claimed in this cycle to prevent collisions
                used_rids = set()

                for w in current_workers:
                    try:
                        elapsed = int(time.time() - w['start_time'])
                        mins, secs = divmod(elapsed, 60)
                        new_worker_times.append(f"{mins}m {secs}s")

                        if self._resolve_worker_identity(w, cached_window_list, used_rids):
                            needs_refresh = True
                        
                        hwnd = w.get("hwnd")
                        rid = w.get("runtime_id")
                        
                        content = None
                        hit = False
                        
                        # Check if active
                        is_active = False
                        if hwnd and win32gui.IsWindow(hwnd):
                            try:
                                cache_key = (hwnd, rid)
                                target_node = self._node_cache.get(cache_key)
                                if not target_node:
                                    _, target_node = self.terminal.get_buffer_text(hwnd, w["terminal"], rid, return_element=True)
                                    if target_node: self._node_cache[cache_key] = target_node

                                if target_node:
                                    if "TabItem" in target_node.ControlTypeName:
                                        sel_pat = target_node.GetSelectionItemPattern()
                                        if sel_pat and sel_pat.IsSelected: is_active = True
                                    else: is_active = True
                            except: pass

                        # PRIORITY 1: Live UIA (Active Tab)
                        if is_active:
                            content = self.terminal.get_buffer_text(hwnd, w["terminal"], rid)
                            if content: hit = True

                        # PRIORITY 2: Log File (Background)
                        log_path = w.get("log_path")
                        if content is None and log_path and os.path.exists(log_path):
                            try:
                                with open(log_path, 'rb') as f:
                                    # Seek to the end and read only the tail
                                    f.seek(0, os.SEEK_END)
                                    size = f.tell()
                                    max_tail = 10000 # Roughly 100-200 lines
                                    offset = max(0, size - max_tail)
                                    f.seek(offset)
                                    raw_bytes = f.read()
                                    
                                # Decode bytes using multiple possible encodings
                                raw_content = None
                                for enc in ['utf-8', 'utf-16', 'utf-16-le', 'cp1252']:
                                    try:
                                        raw_content = raw_bytes.decode(enc, errors='ignore')
                                        if raw_content: break
                                    except: continue
                                            
                                if raw_content:
                                    # Aggressive Filtering: Remove transcript headers and footers
                                    lines = raw_content.splitlines()
                                    clean_lines = []
                                    skip_keywords = ["**********************", "Windows PowerShell transcript", "Username:", "RunAs User:", "Configuration Name:", "Machine:", "Host Application:", "Process ID:", "PSVersion:", "PSEdition:", "OS:", "CLRVersion:", "BuildVersion:", "Start time:", "End time:", "Transcript started, output file is"]
                                    
                                    for line in lines:
                                        if not any(k in line for k in skip_keywords):
                                            clean_lines.append(line)
                                    
                                    # Viewport Emulation: Take the last 60 lines
                                    viewport_lines = clean_lines[-60:]
                                    content = "\n".join(viewport_lines).strip()
                                    hit = True
                            except Exception as e:
                                print(f"[WorkerManager Log Tail Error] {e}")

                        # Check for PROMOTION (ONLY if Active to prevent cross-talk)
                        if not log_path and hwnd and win32gui.IsWindow(hwnd):
                            # Safety: Only promote if this specific worker is CURRENTLY active in the terminal
                            if is_active:
                                # Only promote if we haven't started promoting yet
                                if not w.get("is_promoting"):
                                    w["is_promoting"] = True
                                    new_log = os.path.join(os.environ.get('TEMP', '.'), f"promoted_{int(time.time())}_{w['terminal']}.log")
                                    w["log_path"] = new_log
                                    cmd = f'Start-Transcript -Path "{new_log}" -Append; Clear-Host'
                                    self.terminal.send_command(cmd)
                                    print(f"[WorkerManager] Promoting {w['terminal']} to logging tier...")
                            else:
                                # If not active, we cannot safely inject keystrokes.
                                # The fallback UIA/switch logic will handle it until the user clicks the tab.
                                pass

                        if content is None:
                            if not hwnd or not win32gui.IsWindow(hwnd):
                                if w.get("status") != "Offline":
                                    w["status"] = "Offline"
                                    needs_refresh = True
                                continue

                            # Fallback PRIORITY 3: UIA Cache
                            cache_key = (hwnd, rid)
                            cached_node = self._node_cache.get(cache_key)
                            if cached_node:
                                try:
                                    content = self.terminal.get_text_from_element(cached_node)
                                    if content is not None: hit = True
                                    else: del self._node_cache[cache_key]
                                except: del self._node_cache[cache_key]

                        if content is None:
                            now = time.time()
                            last_switch = w.get("last_switch_time", 0)
                            if now - last_switch > 5:
                                content = self.terminal.capture_with_switch(hwnd, w["terminal"], rid)
                                w["last_switch_time"] = now

                        if content is None:
                            content, new_node = self.terminal.get_buffer_text(hwnd, w["terminal"], rid, return_element=True)
                            if new_node: self._node_cache[(hwnd, rid)] = new_node

                        # Update stats and buffer
                        w["is_cached"] = hit
                        w["hits"] = w.get("hits", 0) + (1 if hit else 0)
                        w["walks"] = w.get("walks", 0) + (1 if not hit else 0)

                        if content is not None:
                            if content != w.get("last_buffer"):
                                w["last_buffer"] = content
                                needs_refresh = True
                            if w.get("status") != "Online":
                                w["status"] = "Online"
                                needs_refresh = True
                            if self.on_buffer_callback:
                                self.on_buffer_callback(hwnd, rid, content)
                        else:
                            if not win32gui.IsWindow(hwnd):
                                if w.get("status") != "Offline":
                                    w["status"] = "Offline"
                                    needs_refresh = True
                    except Exception as e:
                        print(f"[WorkerManager Sync Error] {e}")

                with self.status_lock:
                    self.worker_status_cache = new_worker_times

                if needs_refresh and self.on_update_callback:
                    self.on_update_callback()

                ms = self.full_config.get("terminal", {}).get('sync_interval_ms', 1000)
                time.sleep(ms / 1000.0)