import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import win32gui
import win32con
import pyautogui
import subprocess
import os
import tempfile
import threading
import time

class TerminalConnectorV2:
    def __init__(self, root):
        self.root = root
        self.root.title("Terminal Connector v2 (UIA)")
        self.root.geometry("800x850")
        
        self.connected_hwnd = None
        self.connected_title = None
        self.sync_interval = 1000  # ms
        self.is_syncing = False
        self.capture_lock = threading.Lock()
        
        self.setup_ui()
        self.refresh_window_list()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Search / Filter
        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(filter_frame, text="Search Window:").pack(side=tk.LEFT)
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *args: self.filter_list())
        self.filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_var)
        self.filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(filter_frame, text="Refresh", command=self.refresh_window_list).pack(side=tk.RIGHT)

        # Window List
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.window_listbox = tk.Listbox(list_frame, height=5, font=("Consolas", 9))
        self.window_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.window_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.window_listbox.config(yscrollcommand=scrollbar.set)

        # Terminal Display
        display_frame = ttk.LabelFrame(main_frame, text="Background UIA Terminal Sync", padding="5")
        display_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.terminal_display = scrolledtext.ScrolledText(
            display_frame, 
            state='disabled', 
            bg="#1e1e1e", 
            fg="#d4d4d4", 
            font=("Consolas", 10),
            padx=5,
            pady=5,
            borderwidth=0,
            highlightthickness=0
        )
        self.terminal_display.pack(fill=tk.BOTH, expand=True)

        # Controls
        control_frame = ttk.LabelFrame(main_frame, text="Status & Settings", padding="10")
        control_frame.pack(fill=tk.X, pady=(5, 0))

        self.connect_btn = ttk.Button(control_frame, text="Connect (UIA)", command=self.connect_window)
        self.connect_btn.pack(side=tk.LEFT, padx=5)

        self.auto_sync_var = tk.BooleanVar(value=True)
        self.sync_check = ttk.Checkbutton(control_frame, text="Silent Auto-Sync", variable=self.auto_sync_var)
        self.sync_check.pack(side=tk.LEFT, padx=10)

        self.status_label = ttk.Label(control_frame, text="Status: Disconnected", foreground="red")
        self.status_label.pack(side=tk.RIGHT, padx=10)

        # Command Input
        cmd_frame = ttk.LabelFrame(main_frame, text="Send Command (Requires brief focus)", padding="10")
        cmd_frame.pack(fill=tk.X, pady=(10, 0))

        self.cmd_entry = ttk.Entry(cmd_frame)
        self.cmd_entry.insert(0, "dir")
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.send_btn = ttk.Button(cmd_frame, text="Execute", command=self.send_command, state=tk.DISABLED)
        self.send_btn.pack(side=tk.RIGHT)

        self.all_windows = [] 

    def get_window_list(self):
        windows = []
        def enum_handler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    windows.append((title, hwnd))
        win32gui.EnumWindows(enum_handler, None)
        return sorted(windows, key=lambda x: x[0].lower())

    def refresh_window_list(self):
        self.all_windows = self.get_window_list()
        self.filter_list()

    def filter_list(self):
        search_term = self.filter_var.get().lower()
        self.window_listbox.delete(0, tk.END)
        for title, hwnd in self.all_windows:
            if search_term in title.lower():
                self.window_listbox.insert(tk.END, title)

    def connect_window(self):
        selection = self.window_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a window.")
            return

        selected_title = self.window_listbox.get(selection[0])
        target_hwnd = next((hwnd for title, hwnd in self.all_windows if title == selected_title), None)
        
        if target_hwnd:
            self.connected_hwnd = target_hwnd
            self.connected_title = selected_title
            self.status_label.config(text=f"Connected: {selected_title[:20]}", foreground="green")
            self.send_btn.config(state=tk.NORMAL)
            
            # Start sync loop
            if not self.is_syncing:
                self.is_syncing = True
                self.periodic_sync()

    def periodic_sync(self):
        if self.auto_sync_var.get() and self.connected_title:
            # Run the heavy PS call in a background thread to keep GUI responsive
            threading.Thread(target=self._uia_sync_thread, daemon=True).start()
        
        self.root.after(self.sync_interval, self.periodic_sync)

    def _uia_sync_thread(self):
        if not self.capture_lock.acquire(blocking=False):
            return # Skip if a capture is already in progress
            
        try:
            content = self._get_uia_content(self.connected_title)
            if content:
                self.root.after(0, self.update_display, content)
        finally:
            self.capture_lock.release()

    def _get_uia_content(self, target_title):
        ps_content = r"""
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$targetTitle = "{0}"
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
""" + r"""
$condition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty, $targetTitle)
$element = [System.Windows.Automation.AutomationElement]::RootElement.FindFirst([System.Windows.Automation.TreeScope]::Children, $condition)

if ($element -eq $null) {
    $all = [System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)
    foreach ($item in $all) {
        if ($item.Current.Name -like "*$targetTitle*") {
            $element = $item
            break
        }
    }
}

if ($element -ne $null) {
    $allDescendants = $element.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
    $bestText = ""
    
    foreach ($item in $allDescendants) {
        try {
            $name = $item.Current.Name
            $pattern = $item.GetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern)
            if ($pattern -ne $null) {
                $text = $pattern.DocumentRange.GetText(-1)
                $trimmed = $text.Trim()
                
                # Priority 1: Specifically named buffer
                if ($name -eq "Windows PowerShell" -or $name -eq "Command Prompt") {
                    Write-Host $text
                    exit 0
                }
                
                # Priority 2: Longest text that isn't just the window title
                if ($trimmed.Length -gt $bestText.Length -and $trimmed -ne $targetTitle) {
                    $bestText = $text
                }
            }
        } catch {}
    }
    
    if ($bestText.Length -gt 0) {
        Write-Host $bestText
        exit 0
    }
}
"""
        
        try:
            with tempfile.NamedTemporaryFile(suffix=".ps1", delete=False, mode='w', encoding='utf-8') as tf:
                tf.write(ps_content.format(target_title))
                temp_path = tf.name

            process = subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", temp_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            stdout_bytes, _ = process.communicate()
            
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            return stdout_bytes.decode('utf-8', errors='replace').strip()
        except Exception as e:
            print(f"UIA Error: {e}")
            return None

    def update_display(self, content):
        self.terminal_display.config(state='normal')
        self.terminal_display.delete('1.0', tk.END)
        self.terminal_display.insert(tk.END, content)
        self.terminal_display.see(tk.END)
        self.terminal_display.config(state='disabled')

    def focus_target(self):
        if not self.connected_hwnd or not win32gui.IsWindow(self.connected_hwnd):
            self.status_label.config(text="Status: Lost", foreground="red")
            return False
        
        try:
            if win32gui.IsIconic(self.connected_hwnd):
                win32gui.ShowWindow(self.connected_hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self.connected_hwnd)
            time.sleep(0.05)
            return True
        except Exception:
            return False

    def send_command(self):
        if self.focus_target():
            text = self.cmd_entry.get()
            pyautogui.write(text + "\n", interval=0.02)
            # Return focus to UI
            self.root.focus_force()

if __name__ == "__main__":
    root = tk.Tk()
    app = TerminalConnectorV2(root)
    root.mainloop()
