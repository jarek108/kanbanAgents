import threading
import time
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
                        if not hwnd or not win32gui.IsWindow(hwnd): 
                            if w.get("status") != "Offline":
                                w["status"] = "Offline"
                                needs_refresh = True
                            continue

                        # 3. Capture buffer (Try Cache -> Re-walk)
                        content = None
                        cache_key = (hwnd, rid)
                        cached_node = self._node_cache.get(cache_key)
                        
                        hit = False
                        if cached_node:
                            try:
                                content = self.terminal.get_text_from_element(cached_node)
                                if content:
                                    hit = True
                                else:
                                    del self._node_cache[cache_key]
                            except:
                                del self._node_cache[cache_key]

                        if not content:
                            # Full re-walk capture
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

                        if content:
                            w["last_buffer"] = content
                            if w.get("status") != "Online":
                                w["status"] = "Online"
                                needs_refresh = True
                            
                            if self.on_buffer_callback:
                                self.on_buffer_callback(hwnd, content)
                        else:
                            if w.get("status") != "Offline":
                                w["status"] = "Offline"
                                needs_refresh = True
                    except Exception as e:
                        print(f"[WorkerManager Sync Error] {e}")
                        # Ensure we don't break list indexing on error
                        if len(new_worker_times) < (current_workers.index(w) + 1):
                            new_worker_times.append("Error")

                with self.status_lock:
                    self.worker_status_cache = new_worker_times

                if needs_refresh and self.on_update_callback:
                    self.on_update_callback()

                ms = self.full_config.get("terminal", {}).get('sync_interval_ms', 1000)
                time.sleep(ms / 1000.0)

