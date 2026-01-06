import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import win32gui
import win32process
import win32con
import pyautogui
import pyperclip
import time

class TerminalConnector:
    def __init__(self, root):
        self.root = root
        self.root.title("Terminal Connector")
        self.root.geometry("700x800")
        
        self.connected_hwnd = None
        self.sync_interval = 1000  # ms
        self.is_syncing = False
        
        # UI Elements
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
        display_frame = ttk.LabelFrame(main_frame, text="Live Terminal Output", padding="5")
        display_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.terminal_display = scrolledtext.ScrolledText(
            display_frame, 
            state='disabled', 
            bg="#1e1e1e", 
            fg="#d4d4d4", 
            font=("Consolas", 10),
            padx=5,
            pady=5
        )
        self.terminal_display.pack(fill=tk.BOTH, expand=True)

        # Controls
        control_frame = ttk.LabelFrame(main_frame, text="Connection Controls", padding="10")
        control_frame.pack(fill=tk.X, pady=(5, 0))

        self.connect_btn = ttk.Button(control_frame, text="Connect", command=self.connect_window)
        self.connect_btn.pack(side=tk.LEFT, padx=5)

        self.auto_sync_var = tk.BooleanVar(value=True)
        self.sync_check = ttk.Checkbutton(control_frame, text="Auto-Sync (1s)", variable=self.auto_sync_var)
        self.sync_check.pack(side=tk.LEFT, padx=10)

        self.status_label = ttk.Label(control_frame, text="Status: Disconnected", foreground="red")
        self.status_label.pack(side=tk.RIGHT, padx=10)

        # Command Input
        test_frame = ttk.LabelFrame(main_frame, text="Send Command", padding="10")
        test_frame.pack(fill=tk.X, pady=(10, 0))

        self.test_entry = ttk.Entry(test_frame)
        self.test_entry.insert(0, "dir")
        self.test_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.send_btn = ttk.Button(test_frame, text="Send", command=self.send_command, state=tk.DISABLED)
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
            self.status_label.config(text=f"Connected: {selected_title[:15]}...", foreground="green")
            self.send_btn.config(state=tk.NORMAL)
            
            # Initial Setup: Move and Sync
            self.prepare_window()
            self.sync_content()
            
            # Start periodic sync if not already running
            if not self.is_syncing:
                self.is_syncing = True
                self.periodic_sync()

    def prepare_window(self):
        """Moves window to primary screen and ensures it's visible."""
        if self.connected_hwnd and win32gui.IsWindow(self.connected_hwnd):
            win32gui.ShowWindow(self.connected_hwnd, win32con.SW_RESTORE)
            # Move to a safe area on primary monitor
            win32gui.SetWindowPos(self.connected_hwnd, win32con.HWND_TOP, 10, 10, 800, 600, win32con.SWP_SHOWWINDOW)
            win32gui.SetForegroundWindow(self.connected_hwnd)
            time.sleep(0.1)

    def focus_target(self):
        if not self.connected_hwnd or not win32gui.IsWindow(self.connected_hwnd):
            self.status_label.config(text="Status: Connection Lost", foreground="red")
            self.send_btn.config(state=tk.DISABLED)
            return False
        
        try:
            if win32gui.IsIconic(self.connected_hwnd):
                win32gui.ShowWindow(self.connected_hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self.connected_hwnd)
            return True
        except Exception:
            return False

    def sync_content(self):
        """Captures content using Windows Terminal shortcuts."""
        if not self.focus_target():
            return

        # Use the shortcuts that worked in debug_terminal.py
        try:
            pyperclip.copy("EMPTY") 
            
            # Select All and Copy (Windows Terminal Style)
            pyautogui.hotkey('ctrl', 'shift', 'a')
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'shift', 'c')
            time.sleep(0.1)
            
            content = pyperclip.paste()
            
            if content != "EMPTY":
                self.update_display(content)
            else:
                # Fallback to standard shortcuts
                pyautogui.hotkey('ctrl', 'a')
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.1)
                content = pyperclip.paste()
                if content != "EMPTY":
                    self.update_display(content)
                    
        except Exception as e:
            print(f"Sync Error: {e}")
        finally:
            self.root.focus_force()

    def update_display(self, content):
        self.terminal_display.config(state='normal')
        self.terminal_display.delete('1.0', tk.END)
        self.terminal_display.insert(tk.END, content)
        self.terminal_display.see(tk.END)
        self.terminal_display.config(state='disabled')

    def periodic_sync(self):
        if self.auto_sync_var.get() and self.connected_hwnd:
            self.sync_content()
        self.root.after(self.sync_interval, self.periodic_sync)

    def send_command(self):
        if self.focus_target():
            text = self.test_entry.get()
            # Use slow typing as established in debug
            pyautogui.write(text + "\n", interval=0.05)
            # Short delay then sync immediately
            self.root.after(500, self.sync_content)

if __name__ == "__main__":
    root = tk.Tk()
    app = TerminalConnector(root)
    root.mainloop()


if __name__ == "__main__":
    root = tk.Tk()
    app = TerminalConnector(root)
    root.mainloop()