import win32gui
import win32process
import win32con
import pyautogui
import subprocess
import os
import tempfile
import threading
import time
import json
import engine_events
import uiautomation as auto

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "orchestrator_config.json")

def load_config():
    if not os.path.exists(CONFIG_FILE): return {}
    with open(CONFIG_FILE, 'r') as f: return json.load(f).get("terminal", {})

def save_config(updates):
    if not os.path.exists(CONFIG_FILE): return
    with open(CONFIG_FILE, 'r') as f: full_cfg = json.load(f)
    full_cfg.setdefault("terminal", {}).update(updates)
    with open(CONFIG_FILE, 'w') as f: json.dump(full_cfg, f, indent=4)

class TerminalEngine:
    def __init__(self):
        self.connected_hwnd = None
        self.connected_title = None
        self.connected_runtime_id = None
        self.capture_lock = threading.Lock()
        # Initialize UIA settings for speed
        auto.SetGlobalSearchTimeout(1)

    def get_window_list(self):
        """Native Discovery: Finds terminal HWNDs and probes for tabs via uiautomation."""
        terminal_hwnds = []
        classes = ["ConsoleWindowClass", "CASCADIA_HOST_HTTP_WINDOW_CLASS", "CASCADIA_HOSTING_WINDOW_CLASS"]
        
        def enum_handler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetClassName(hwnd) in classes:
                terminal_hwnds.append(hwnd)
        win32gui.EnumWindows(enum_handler, None)

        discovered = []
        for hwnd in terminal_hwnds:
            try:
                element = auto.ControlFromHandle(hwnd)
                if not element: continue
                
                win_name = element.Name
                win_id = ",".join(map(str, element.GetRuntimeId()))
                if win_name: discovered.append((win_name, hwnd, win_id))

                # Search for Tabs
                for child in element.GetChildren():
                    # Look for TabItems or similar
                    ctype = child.ControlTypeName
                    if ctype in ["TabItemControl", "ListItemControl"]:
                        name = child.Name
                        if name:
                            rid = ",".join(map(str, child.GetRuntimeId()))
                            discovered.append((name, hwnd, rid))
            except Exception as e:
                print(f"[UIA Discovery Error] {e}")

        return sorted(list(set(discovered)), key=lambda x: x[0].lower())

    def connect(self, hwnd, title, runtime_id=None):
        self.connected_hwnd = hwnd
        self.connected_title = title
        self.connected_runtime_id = runtime_id
        save_config({"last_title": title, "last_id": runtime_id})
        engine_events.emit("terminal_connected", {"title": title, "hwnd": hwnd, "runtime_id": runtime_id})
        return True

    def disconnect(self):
        title = self.connected_title
        self.connected_hwnd = None
        self.connected_title = None
        self.connected_runtime_id = None
        engine_events.emit("terminal_disconnected", {"title": title})

    def send_command(self, cmd):
        if not self.connected_hwnd or not win32gui.IsWindow(self.connected_hwnd): return False
        try:
            if win32gui.IsIconic(self.connected_hwnd): win32gui.ShowWindow(self.connected_hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self.connected_hwnd)
            time.sleep(0.05)
            pyautogui.write(cmd + "\n", interval=0.01)
            return True
        except: return False

    def get_buffer_text(self, hwnd=None, title=None, runtime_id=None):
        """Native capture using uiautomation."""
        target_hwnd = hwnd or self.connected_hwnd
        target_title = title or self.connected_title
        target_id = runtime_id or self.connected_runtime_id

        if not target_hwnd or not win32gui.IsWindow(target_hwnd): return None
        
        try:
            # 1. Try targeting by RuntimeId
            target_element = None
            if target_id:
                id_tuple = tuple(map(int, target_id.split(',')))
                # Search for element with this runtime ID
                root = auto.ControlFromHandle(target_hwnd)
                if root:
                    if tuple(root.GetRuntimeId()) == id_tuple:
                        target_element = root
                    else:
                        target_element = auto.Control(searchDepth=5, RuntimeId=id_tuple)

            # 2. Fallback to Name
            if not target_element and target_title:
                target_element = auto.Control(searchDepth=5, Name=target_title)

            if not target_element: return None

            # Find text pattern
            for child in target_element.GetDescendants():
                if child.ControlTypeName in ["PaneControl", "DocumentControl", "EditControl"]:
                    try:
                        # Some terminals use TextPattern, others just have a Name or Value
                        pattern = child.GetTextPattern()
                        if pattern:
                            text = pattern.DocumentRange.GetText(-1)
                            if text and len(text.strip()) > 5:
                                return text
                    except: pass
            
            return None
        except Exception as e:
            # print(f"[Capture Error] {e}")
            return None
