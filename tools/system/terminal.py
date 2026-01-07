import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
from terminal_core import TerminalCore

class TerminalUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Terminal Connector v2 (UIA)")
        
        self.core = TerminalCore()
        self.root.geometry(self.core.config.get("last_geometry", "1000x400"))
        self.root.configure(bg="#1e1e1e")
        
        self.is_syncing = False
        
        self.setup_styles()
        self.setup_ui()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.after(500, self.auto_connect)

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background="#1e1e1e")
        self.style.configure("TLabel", background="#1e1e1e", foreground="#d4d4d4", font=("Segoe UI", 9))
        self.style.configure("TButton", padding=3, font=("Segoe UI", 9))
        self.style.configure("Header.TFrame", background="#2d2d2d")
        self.style.configure("Header.TLabel", background="#2d2d2d", font=("Segoe UI", 9, "bold"))
        self.style.configure("TLabelframe", background="#1e1e1e", foreground="#007acc", font=("Segoe UI", 9, "bold"))
        self.style.configure("TLabelframe.Label", background="#1e1e1e", foreground="#007acc")

    def setup_ui(self):
        self.main_container = ttk.Frame(self.root, padding="10")
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # --- HEADER ---
        self.header_bar = ttk.Frame(self.main_container, style="Header.TFrame", padding="5")
        self.header_bar.pack(fill=tk.X, side=tk.TOP, pady=(0, 5))

        ttk.Button(self.header_bar, text="Select Window", command=self.open_selection_popup).pack(side=tk.LEFT, padx=(0, 10))
        self.action_btn = ttk.Button(self.header_bar, text="Reconnect", command=self.toggle_connection)
        self.action_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.status_icon = tk.Label(self.header_bar, text="●", fg="red", bg="#2d2d2d", font=("Segoe UI", 11))
        self.status_icon.pack(side=tk.LEFT)
        self.status_label = ttk.Label(self.header_bar, text="Disconnected", style="Header.TLabel")
        self.status_label.pack(side=tk.LEFT, padx=(2, 15))

        self.auto_sync_var = tk.BooleanVar(value=self.core.config['auto_sync'])
        tk.Checkbutton(self.header_bar, text="Mirroring", variable=self.auto_sync_var, 
                       command=self.toggle_auto_sync, bg="#2d2d2d", fg="#d4d4d4", 
                       selectcolor="#1e1e1e", activebackground="#2d2d2d", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=5)

        ttk.Label(self.header_bar, text="Sync(ms):", style="Header.TLabel").pack(side=tk.LEFT, padx=(10, 2))
        self.sync_val_var = tk.StringVar(value=str(self.core.config['sync_interval_ms']))
        self.sync_entry = tk.Entry(self.header_bar, textvariable=self.sync_val_var, width=5, bg="#1e1e1e", fg="#d4d4d4", borderwidth=0)
        self.sync_entry.pack(side=tk.LEFT, padx=5)
        self.sync_entry.bind("<Return>", self.update_sync_interval)

        self.output_visible = tk.BooleanVar(value=False)
        self.toggle_output_btn = ttk.Button(self.header_bar, text="▼ Show Live", command=self.toggle_output_panel)
        self.toggle_output_btn.pack(side=tk.RIGHT, padx=5)

        # --- Terminal Mirror ---
        self.display_frame = ttk.LabelFrame(self.main_container, text=" Terminal Mirror ", padding="5")
        self.terminal_display = scrolledtext.ScrolledText(
            self.display_frame, state='disabled', bg="#000000", fg="#d4d4d4", font=("Consolas", 10),
            padx=10, pady=10, borderwidth=0, highlightthickness=0
        )
        self.terminal_display.pack(fill=tk.BOTH, expand=True)

        # --- Command Field ---
        self.cmd_frame = ttk.LabelFrame(self.main_container, text=" Send Command ", padding="10")
        self.cmd_frame.pack(fill=tk.X, side=tk.TOP, pady=(5, 0))
        self.cmd_entry = ttk.Entry(self.cmd_frame)
        self.cmd_entry.pack(fill=tk.X, expand=True, padx=5)
        self.cmd_entry.bind("<Return>", self.send_command)

    def on_closing(self):
        self.core.save_config({"last_geometry": self.root.geometry()})
        self.root.destroy()

    def toggle_output_panel(self):
        if self.output_visible.get():
            self.display_frame.pack_forget()
            self.toggle_output_btn.config(text="▼ Show Live")
            self.output_visible.set(False)
        else:
            self.cmd_frame.pack_forget()
            self.display_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP, pady=5)
            self.cmd_frame.pack(fill=tk.X, side=tk.TOP, pady=(5, 0))
            self.toggle_output_btn.config(text="▲ Hide Live")
            self.output_visible.set(True)

    def open_selection_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Select Terminal Window")
        popup.geometry("400x300")
        popup.configure(bg="#1e1e1e")
        
        # Center on parent
        self.root.update_idletasks()
        px = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - 200
        py = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - 150
        popup.geometry(f"+{px}+{py}")
        
        popup.transient(self.root)
        popup.grab_set()

        frame = ttk.Frame(popup, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Search Window:").pack(fill=tk.X)
        search_var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=search_var)
        entry.pack(fill=tk.X, pady=5)
        entry.focus_set()

        listbox = tk.Listbox(frame, bg="#2d2d2d", fg="#d4d4d4", borderwidth=0, font=("Consolas", 9))
        listbox.pack(fill=tk.BOTH, expand=True)

        def populate_list():
            listbox.delete(0, tk.END)
            term = search_var.get().lower()
            windows = self.core.get_window_list()
            for title, hwnd in windows:
                if term in title.lower(): listbox.insert(tk.END, title)

        search_var.trace_add("write", lambda *args: populate_list())
        populate_list()

        def on_select():
            selection = listbox.curselection()
            if selection:
                title = listbox.get(selection[0])
                windows = self.core.get_window_list()
                hwnd = next((h for t, h in windows if t == title), None)
                if hwnd: 
                    self.connect_to_hwnd(hwnd, title)
                    popup.destroy()

        ttk.Button(frame, text="Connect", command=on_select).pack(pady=10)
        listbox.bind("<Double-Button-1>", lambda e: on_select())

    def toggle_connection(self):
        if self.core.connected_hwnd: self.disconnect()
        else: self.auto_connect()

    def disconnect(self):
        self.core.disconnect()
        self.status_icon.config(fg="red")
        self.status_label.config(text="Disconnected")
        self.action_btn.config(text="Reconnect")

    def auto_connect(self):
        target = self.core.config.get("last_title")
        if not target: return
        windows = self.core.get_window_list()
        for title, hwnd in windows:
            if target.lower() in title.lower(): self.connect_to_hwnd(hwnd, title); return

    def connect_to_hwnd(self, hwnd, title):
        if self.core.connect_to_hwnd(hwnd, title):
            self.status_icon.config(fg="green")
            self.status_label.config(text=f"Connected: {title[:20]}...")
            self.action_btn.config(text="Disconnect")
            if not self.is_syncing:
                self.is_syncing = True
                self.periodic_sync()

    def update_sync_interval(self, event=None):
        try:
            val = int(self.sync_val_var.get())
            if val < 100: val = 100
            self.core.save_config({'sync_interval_ms': val})
            self.sync_val_var.set(str(val))
            self.root.focus_set()
        except: self.sync_val_var.set(str(self.core.config['sync_interval_ms']))

    def toggle_auto_sync(self): 
        self.core.save_config({"auto_sync": self.auto_sync_var.get()})

    def periodic_sync(self):
        if self.auto_sync_var.get() and self.core.connected_title:
            threading.Thread(target=self._uia_sync_thread, daemon=True).start()
        ms = self.core.config.get('sync_interval_ms', 1000)
        self.root.after(ms, self.periodic_sync)

    def _uia_sync_thread(self):
        content = self.core.get_buffer_text()
        if content:
            self.root.after(0, self.update_display, content)

    def update_display(self, content):
        self.terminal_display.config(state='normal')
        self.terminal_display.delete('1.0', tk.END)
        self.terminal_display.insert(tk.END, content)
        self.terminal_display.see(tk.END)
        self.terminal_display.config(state='disabled')

    def send_command(self, event=None):
        cmd = self.cmd_entry.get()
        if not cmd: return
        if self.core.send_command(cmd):
            self.cmd_entry.delete(0, tk.END)
            self.root.focus_force()

if __name__ == "__main__":
    root = tk.Tk()
    app = TerminalUI(root)
    root.mainloop()
