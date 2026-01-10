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
    return data.get("terminal", {})

def save_config(updates):
    data = utils_ui.load_full_config()
    data.setdefault("terminal", {}).update(updates)
    utils_ui.save_full_config(data)



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

                # Use WalkControl to find all TabItems recursively
                for child, depth in auto.WalkControl(element, maxDepth=10):
                    if child.ControlTypeName in ["TabItemControl", "ListItemControl"]:
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

    def get_process_cwd(self, hwnd):
        """Attempts to find the current working directory of the process owning the HWND."""
        import psutil
        import win32process
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            # Shells like CMD/PowerShell usually keep the CWD. 
            # If it's a wrapper (like WindowsTerminal), we might need to look at children.
            cwd = process.cwd()
            
            # If it's Windows Terminal or similar, probe children
            if process.name().lower() in ["windowsterminal.exe", "openconsole.exe"]:
                for child in process.children(recursive=True):
                    try:
                        if child.name().lower() in ["pwsh.exe", "powershell.exe", "cmd.exe", "bash.exe"]:
                            return child.cwd()
                    except: pass
            return cwd
        except:
            return None

    def get_text_from_element(self, element):
        """Extracts text from a cached UIA element."""
        try:
            pattern = element.GetTextPattern()
            if pattern:
                return pattern.DocumentRange.GetText(-1)
        except:
            pass
        return None

    def get_buffer_text(self, hwnd=None, title=None, runtime_id=None, return_element=False):
        """Native capture using uiautomation."""
        target_hwnd = hwnd or self.connected_hwnd
        target_title = title or self.connected_title
        target_id = runtime_id or self.connected_runtime_id

        if not target_hwnd or not win32gui.IsWindow(target_hwnd): return (None, None) if return_element else None
        
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

            if not target_element: return (None, None) if return_element else None

            # Find text pattern using WalkControl
            for child, depth in auto.WalkControl(target_element, maxDepth=12):
                if child.ControlTypeName in ["PaneControl", "DocumentControl", "EditControl"]:
                    text = self.get_text_from_element(child)
                    if text and len(text.strip()) > 5:
                        return (text, child) if return_element else text
            
            return (None, None) if return_element else None
        except Exception as e:
            return (None, None) if return_element else None

