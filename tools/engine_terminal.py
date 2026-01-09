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
        self.connected_runtime_id = None
        self.capture_lock = threading.Lock()

    def get_window_list(self):
        """Surgical Discovery: Finds terminal HWNDs via Win32, then probes for tabs via UIA."""
        import win32gui
        
        terminal_hwnds = []
        classes = ["ConsoleWindowClass", "CASCADIA_HOST_HTTP_WINDOW_CLASS", "CASCADIA_HOSTING_WINDOW_CLASS"]
        
        def enum_handler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetClassName(hwnd) in classes:
                terminal_hwnds.append(str(hwnd))
        win32gui.EnumWindows(enum_handler, None)

        if not terminal_hwnds: return []

        # Pass specific HWNDs to PowerShell to avoid crawling the whole desktop
        hwnd_str = ",".join(terminal_hwnds)
        ps_discovery = r"""
Add-Type -AssemblyName UIAutomationClient
$hwnds = @({0})
$results = @()

foreach ($hwnd in $hwnds) {{
    try {{
        $element = [System.Windows.Automation.AutomationElement]::FromHandle($hwnd)
        if ($element -ne $null) {{
            # 1. Add the main window title
            $winName = $element.Current.Name
            $winId = $element.GetRuntimeId() -join ","
            if ($winName) {{ $results += "$winName|$hwnd|$winId" }}

            # 2. Search for anything that looks like a Tab or Title element
            $condition = [System.Windows.Automation.Condition]::TrueCondition
            $children = $element.FindAll([System.Windows.Automation.TreeScope]::Descendants, $condition)
            
            foreach ($child in $children) {{
                $type = $child.Current.ControlType.ProgrammaticName
                $name = $child.Current.Name
                
                # Filter for likely tab elements: TabItem control type OR elements in the top area
                if ($name -and ($type -match "TabItem|ListItem")) {{
                    $runtimeId = $child.GetRuntimeId() -join ","
                    $results += "$name|$hwnd|$runtimeId"
                }}
            }}
        }}
    }} catch {{}}
}}
$results | Select-Object -Unique
""".format(hwnd_str)

        try:
            with tempfile.NamedTemporaryFile(suffix=".ps1", delete=False, mode='w', encoding='utf-8') as tf:
                tf.write(ps_discovery)
                temp_path = tf.name
            
            process = subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", temp_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
            out, _ = process.communicate()
            if os.path.exists(temp_path): os.remove(temp_path)
            
            lines = out.decode('utf-8', errors='replace').strip().split('\r\n')
            discovered = []
            for line in lines:
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) == 3:
                        discovered.append((parts[0].strip(), int(parts[1]), parts[2].strip()))
            
            return sorted(list(set(discovered)), key=lambda x: x[0].lower())
        except Exception as e:
            print(f"[Discovery Error] {e}")
            return []

    def connect(self, hwnd, title, runtime_id=None):
        self.connected_hwnd = hwnd
        self.connected_title = title
        self.connected_runtime_id = runtime_id
        save_config({"last_title": title, "last_id": runtime_id})
        engine_events.emit("terminal_connected", {"title": title, "hwnd": hwnd, "runtime_id": runtime_id})
        return True

    def get_buffer_text(self):
        """Captures terminal text buffer using UIA. Targeted by HWND + Title + ID."""
        if not self.connected_hwnd or not win32gui.IsWindow(self.connected_hwnd): return None
        if not self.connected_title: return None
        if not self.capture_lock.acquire(blocking=False): return None
        try:
            # Targeted capture using parent HWND, Tab Name, and Runtime ID
            content = self._execute_uia_capture(self.connected_hwnd, self.connected_title, self.connected_runtime_id)
            if content: engine_events.emit("terminal_update", content)
            return content
        finally: self.capture_lock.release()

    def _execute_uia_capture(self, target_hwnd, target_title, target_id=None):
        ps_content = r"""
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$targetHwnd = {0}
$targetTitle = "{1}"
$targetId = "{2}"
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

# Jump directly to the host window
$element = [System.Windows.Automation.AutomationElement]::FromHandle($targetHwnd)

if ($element -ne $null) {{
    $target = $null

    # 1. Try targeting by RuntimeId if available
    if ($targetId) {{
        $idArray = $targetId.Split(',') | ForEach-Object {{ [int]$_ }}
        $idCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::RuntimeIdProperty, $idArray)
        $target = $element.FindFirst([System.Windows.Automation.TreeScope]::Subtree, $idCond)
    }}

    # 2. Fallback to targeting by Name if ID failed or not provided
    if ($target -eq $null) {{
        $titleCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty, $targetTitle)
        $target = $element.FindFirst([System.Windows.Automation.TreeScope]::Subtree, $titleCond)
    }}
    
    # 3. Last fallback to the window itself
    if ($target -eq $null) {{
        if ($element.Current.Name -eq $targetTitle) {{
            $target = $element
        }}
    }}

    if ($target -ne $null) {{
        $allDescendants = $target.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
        $bestText = ""
        
        foreach ($item in $allDescendants) {{
            try {{
                $pattern = $item.GetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern)
                if ($pattern -ne $null) {{
                    $text = $pattern.DocumentRange.GetText(-1)
                    $trimmed = $text.Trim()
                    $name = $item.Current.Name
                    
                    if ($trimmed.Length -gt 5) {{
                        if ($name -match "PowerShell|Command Prompt|Terminal|Console|Text Area") {{
                            Write-Host $text
                            exit 0
                        }}
                        if ($trimmed.Length -gt $bestText.Length) {{
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
}}
""".format(target_hwnd, target_title, target_id if target_id else "")
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
