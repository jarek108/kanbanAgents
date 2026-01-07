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
        self.capture_lock = threading.Lock()

    def get_window_list(self):
        windows = []
        def enum_handler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title: windows.append((title, hwnd))
        win32gui.EnumWindows(enum_handler, None)
        return sorted(windows, key=lambda x: x[0].lower())

    def connect(self, hwnd, title):
        self.connected_hwnd = hwnd
        self.connected_title = title
        save_config({"last_title": title})
        engine_events.emit("terminal_connected", {"title": title, "hwnd": hwnd})
        return True

    def disconnect(self):
        title = self.connected_title
        self.connected_hwnd = None
        self.connected_title = None
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

    def get_buffer_text(self):
        """Captures terminal text buffer using UIA. SILENT method."""
        if not self.connected_hwnd or not win32gui.IsWindow(self.connected_hwnd): return None
        if not self.capture_lock.acquire(blocking=False): return None
        try:
            _, pid = win32process.GetWindowThreadProcessId(self.connected_hwnd)
            content = self._execute_uia_capture(self.connected_hwnd, pid)
            if content: engine_events.emit("terminal_update", content)
            return content
        finally: self.capture_lock.release()

    def _execute_uia_capture(self, hwnd, pid):
        ps_content = r"""
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$hwnd = {0}
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$element = [System.Windows.Automation.AutomationElement]::FromHandle($hwnd)

if ($element -ne $null) {{
    # Enumerate all descendants and find the best text source
    $all = $element.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
    $bestText = ""
    $windowTitle = $element.Current.Name
    
    foreach ($item in $all) {{
        try {{
            $pattern = $item.GetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern)
            if ($pattern -ne $null) {{
                $text = $pattern.DocumentRange.GetText(-1)
                $trimmed = $text.Trim()
                $name = $item.Current.Name
                
                # Logic: We want long text that isn't just the window title or shell name
                if ($trimmed.Length -gt 5) {{
                    # If it's significantly long, it's likely the buffer
                    if ($trimmed.Length -gt 50) {{
                        Write-Host $text
                        exit 0
                    }}
                    
                    # If it's not the window title and longer than what we have, keep it
                    if ($trimmed -ne $windowTitle -and $name -ne $windowTitle -and $trimmed.Length -gt $bestText.Length) {{
                        $bestText = $text
                    }}
                }}
            }}
        }} catch {{}}
    }}
    
    if ($bestText.Length -gt 0) {{
        Write-Host $bestText
        exit 0
    }}
}}
"""
        try:
            with tempfile.NamedTemporaryFile(suffix=".ps1", delete=False, mode='w', encoding='utf-8') as tf:
                tf.write(ps_content)
                temp_path = tf.name
            process = subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", temp_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
            out, err = process.communicate()
            if os.path.exists(temp_path): os.remove(temp_path)
            return out.decode('utf-8', errors='replace').strip()
        except:
            return None
