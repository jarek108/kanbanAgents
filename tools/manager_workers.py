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
        self.on_buffer_callback = None # (hwnd, content)

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

    def _resolve_worker_identity(self, w, current_window_list):
        """Finds HWND and Runtime ID for a worker based on its terminal title using a provided window list."""
        if w.get("hwnd") and win32gui.IsWindow(w["hwnd"]):
            return False # Already resolved and valid

        for title, hwnd, rid in current_window_list:
            if w["terminal"] == title:
                w["hwnd"] = hwnd
                w["runtime_id"] = rid
                short_rid = rid.split("-")[-1] if rid and "-" in rid else (rid[:8] if rid else "?")
                w["id"] = f"{hwnd}:{short_rid}"
                return True
        return False

    def _uia_sync_loop(self):
        """Persistent background thread for multi-worker mirroring with node caching and window list sharing."""
        with auto.UIAutomationInitializerInThread():
            while self.is_syncing:
                with self.status_lock:
                    current_workers = list(self.workers)

                needs_refresh = False
                new_worker_times = []
                
                # Fetch window list ONCE per cycle to share among all offline workers
                cached_window_list = self.terminal.get_window_list()

                for w in current_workers:
                    try:
                        # 1. Update Elapsed Time
                        elapsed = int(time.time() - w['start_time'])
                        mins, secs = divmod(elapsed, 60)
                        new_worker_times.append(f"{mins}m {secs}s")

                        # 2. Resolve HWND/ID if missing (using shared window list)
                        if self._resolve_worker_identity(w, cached_window_list):
                            needs_refresh = True
                        
                        hwnd = w.get("hwnd")
                        rid = w.get("runtime_id")
                        
                        # 3. Capture buffer (Try Live UIA if Active -> Try Log File -> Fallback)
                        content = None
                        hit = False
                        
                        # Check if this tab is the ACTIVE one in its window
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
                                    else: is_active = True # Standalone window
                            except: pass

                        # PRIORITY 1: Live UIA (Only for the Active Tab for live typing)
                        if is_active:
                            content = self.terminal.get_buffer_text(hwnd, w["terminal"], rid)
                            if content: hit = True

                        # PRIORITY 2: Log File (For Background Tabs or if UIA failed)
                        if content is None:
                            log_path = w.get("log_path")
                            if log_path and os.path.exists(log_path):
                                for enc in ['utf-8', 'utf-16', 'utf-16-le', 'cp1252']:
                                    try:
                                        with open(log_path, 'r', encoding=enc, errors='ignore') as f:
                                            raw_content = f.read()
                                        if raw_content:
                                            # Filter out Transcript metadata
                                            lines = raw_content.splitlines()
                                            clean_lines = []
                                            skip_keywords = ["**********************", "Windows PowerShell transcript start", "Windows PowerShell transcript end", "Username:", "RunAs User:", "Configuration Name:", "Machine:", "Host Application:", "Process ID:", "PSVersion:", "PSEdition:", "OS:", "CLRVersion:", "BuildVersion:", "Start time:", "End time:"]
                                            for line in lines:
                                                if not any(k in line for k in skip_keywords): clean_lines.append(line)
                                            content = "\n".join(clean_lines).strip()
                                            hit = True
                                            break
                                    except: continue

                        if content is None:
                            # If no log, and no window, it's definitely offline
                            if not hwnd or not win32gui.IsWindow(hwnd):
                                if w.get("status") != "Offline":
                                    w["status"] = "Offline"
                                    needs_refresh = True
                                continue

                            # Try to PROMOTE a connected tab to logging if it's Online but has no log
                            if not log_path and w.get("status") == "Online":
                                # Create a log path
                                new_log = os.path.join(os.environ.get('TEMP', '.'), f"promoted_{int(time.time())}_{w['terminal']}.log")
                                w["log_path"] = new_log
                                # Inject the command to start transcription
                                cmd = f'Start-Transcript -Path "{new_log}" -Append; Clear-Host'
                                self.terminal.send_command(cmd)
                                print(f"[WorkerManager] Promoting {w['terminal']} to logging tier...")

                            # Fallback PRIORITY 3: UIA Cache (for non-active tabs without logs)
                            cache_key = (hwnd, rid)
                            cached_node = self._node_cache.get(cache_key)
                            if cached_node:
                                try:
                                    content = self.terminal.get_text_from_element(cached_node)
                                    if content is not None: hit = True
                                    else: del self._node_cache[cache_key]
                                except: del self._node_cache[cache_key]

                        if content is None:
                            # If it's a tab and not selected, get_buffer_text returned None.
                            # We can try capture_with_switch if enough time has passed.
                            now = time.time()
                            last_switch = w.get("last_switch_time", 0)
                            
                            # Only switch if it's been at least 5 seconds since last switch
                            if now - last_switch > 5:
                                content = self.terminal.capture_with_switch(
                                    hwnd=hwnd,
                                    title=w["terminal"],
                                    runtime_id=rid
                                )
                                w["last_switch_time"] = now
                                if content:
                                    # We don't want to cache the node if we had to switch,
                                    # because the buffer element might be volatile.
                                    pass
                            else:
                                # Use last buffer if available to avoid flicker/status change
                                content = w.get("last_buffer")

                        if content is None:
                            # Full re-walk capture (fallback/initial)
                            content, new_node = self.terminal.get_buffer_text(
                                hwnd=hwnd, 
                                title=w["terminal"], 
                                runtime_id=rid,
                                return_element=True
                            )
                            if new_node:
                                self._node_cache[cache_key] = new_node

                        # Update stats
                        w["is_cached"] = hit
                        w["hits"] = w.get("hits", 0) + (1 if hit else 0)
                        w["walks"] = w.get("walks", 0) + (1 if not hit else 0)

                        if content is not None:
                            w["last_buffer"] = content
                            if w.get("status") != "Online":
                                w["status"] = "Online"
                                needs_refresh = True
                            
                            if self.on_buffer_callback:
                                self.on_buffer_callback(hwnd, content)
                        else:
                            # Only mark offline if the window is gone or terminal.get_buffer_text returned None for element too
                            if not win32gui.IsWindow(hwnd):
                                if w.get("status") != "Offline":
                                    w["status"] = "Offline"
                                    needs_refresh = True
                    except Exception as e:
                        print(f"[WorkerManager Sync Error] {e}")
                        if len(new_worker_times) < (current_workers.index(w) + 1):
                            new_worker_times.append("Error")

                with self.status_lock:
                    self.worker_status_cache = new_worker_times

                if needs_refresh and self.on_update_callback:
                    self.on_update_callback()

                ms = self.full_config.get("terminal", {}).get('sync_interval_ms', 1000)
                time.sleep(ms / 1000.0)


