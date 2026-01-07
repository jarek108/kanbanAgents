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
        if not self.connected_hwnd or not win32gui.IsWindow(self.connected_hwnd): return None
        if not self.capture_lock.acquire(blocking=False): return None
        try:
            # 1. Try UIA first
            _, pid = win32process.GetWindowThreadProcessId(self.connected_hwnd)
            content = self._execute_uia_capture(self.connected_hwnd, pid)
            
            # 2. Fallback to Clipboard if UIA returns nothing or is too short
            if not content or len(content) < 10:
                content = self._get_buffer_text_clipboard()
                
            if content: engine_events.emit("terminal_update", content)
            return content
        finally: self.capture_lock.release()

    def _get_buffer_text_clipboard(self):
        """Captures buffer via Ctrl+A, Ctrl+C fallback."""
        import pyperclip
        if not self.connected_hwnd or not win32gui.IsWindow(self.connected_hwnd): return None
        
        try:
            # Save old clipboard
            old = pyperclip.paste()
            
            # Focus and interact
            if win32gui.IsIconic(self.connected_hwnd): win32gui.ShowWindow(self.connected_hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self.connected_hwnd)
            time.sleep(0.1)
            
            # Try Ctrl+Shift+A/C first (Windows Terminal)
            pyautogui.hotkey('ctrl', 'shift', 'a')
            time.sleep(0.05)
            pyautogui.hotkey('ctrl', 'shift', 'c')
            time.sleep(0.1)
            
            content = pyperclip.paste()
            if content != old and len(content) > 10:
                return content
                
            # Try standard Ctrl+A/C
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.05)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.1)
            
            content = pyperclip.paste()
            return content if content != old else None
        except:
            return None

    def _execute_uia_capture(self, hwnd, pid):
        ps_content = r"""
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$hwnd = {0}
$pid = {1}
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

# Prioritize HWND as it's a direct link to the window
$element = [System.Windows.Automation.AutomationElement]::FromHandle($hwnd)

if ($element -eq $null -and $pid -ne 0) {{
    # Fallback to PID search if HWND failed
    $element = [System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition) | Where-Object {{ $_.Current.ProcessId -eq $pid }} | Select-Object -First 1
}}

if ($element -ne $null) {{
    # Try multiple ways to get text
    $bestText = ""
    # DEBUG: Write-Host "DEBUG_PROPS: Name=$($element.Current.Name) PID=$($element.Current.ProcessId) Type=$($element.Current.ControlType.ProgrammaticName)"
    
    # 1. Check if the element itself has a ValuePattern
    try {{
        $valPattern = $element.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)
        if ($valPattern -ne $null) {{
            $bestText = $valPattern.Current.Value
            if ($bestText.Length -gt 10) {{ Write-Host $bestText; exit 0 }}
        }}
    }} catch {{}}

    # 2. Search descendants
    $allDescendants = $element.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
    
    foreach ($item in $allDescendants) {{
        try {{
            $name = $item.Current.Name
            
            # Try TextPattern
            $pattern = $item.GetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern)
            if ($pattern -ne $null) {{
                $text = $pattern.DocumentRange.GetText(-1)
                if ($text.Length -gt 10) {{
                    if ($name -match "PowerShell|Command Prompt|Terminal|Console|Text Area") {{ Write-Host $text; exit 0 }}
                    if ($text.Length -gt $bestText.Length) {{ $bestText = $text }}
                }}
            }}
            
            # Try ValuePattern fallback
            $vPattern = $item.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)
            if ($vPattern -ne $null) {{
                $vText = $vPattern.Current.Value
                if ($vText.Length -gt $bestText.Length) {{ $bestText = $vText }}
            }}
        }} catch {{}} 
    }}
    if ($bestText) {{ Write-Host $bestText; exit 0 }}
}}
# If no text found, script will exit naturally with no output
""".format(hwnd, pid)
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