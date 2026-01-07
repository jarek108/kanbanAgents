import win32gui
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
    full_cfg.get("terminal", {}).update(updates)
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
        if not self.connected_title: return None
        if not self.capture_lock.acquire(blocking=False): return None
        try:
            content = self._execute_uia_capture(self.connected_title)
            if content: engine_events.emit("terminal_update", content)
            return content
        finally: self.capture_lock.release()

    def _execute_uia_capture(self, target_title):
        ps_content = r"""
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$targetTitle = "{0}"
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$element = [System.Windows.Automation.AutomationElement]::RootElement.FindFirst([System.Windows.Automation.TreeScope]::Descendants, 
    (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty, $targetTitle)))
if ($element -eq $null) {{
    $all = [System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)
    foreach ($item in $all) {{ if ($item.Current.Name -like "*$targetTitle*") {{ $element = $item; break }} }}
}}
if ($element -ne $null) {{
    $allDescendants = $element.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
    $bestText = ""
    foreach ($item in $allDescendants) {{
        try {{
            $pattern = $item.GetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern)
            if ($pattern -ne $null) {{
                $text = $pattern.DocumentRange.GetText(-1)
                if ($text.Length -gt 10) {{
                    if ($item.Current.Name -match "PowerShell|Command Prompt|Terminal|Console|Text Area") {{ Write-Host $text; exit 0 }}
                    if ($text.Length -gt $bestText.Length -and $item.Current.Name -ne $targetTitle) {{ $bestText = $text }}
                }}
            }}
        }} catch {{}} 
    }}
    if ($bestText) {{ Write-Host $bestText; exit 0 }}
}}
""".format(target_title)
        try:
            with tempfile.NamedTemporaryFile(suffix=".ps1", delete=False, mode='w', encoding='utf-8') as tf: tf.write(ps_content); temp_path = tf.name
            process = subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", temp_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
            out, _ = process.communicate()
            if os.path.exists(temp_path): os.remove(temp_path)
            return out.decode('utf-8', errors='replace').strip()
        except: return None
