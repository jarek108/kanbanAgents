import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import os
import json
import webbrowser
import engine_terminal
import engine_kanban
import engine_projects
import engine_events

class OrchestratorUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Project Orchestrator v3")
        
        # Load main config for UI state
        self.full_config = self._load_full_config()
        self.root.geometry(self.full_config.get("ui", {}).get("orch_geometry", "1100x700"))
        self.root.configure(bg="#1e1e1e")
        
        self.terminal = engine_terminal.TerminalEngine()
        self.is_syncing = False
        self.active_project = None
        
        self.setup_styles()
        self.setup_ui()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Load initial project
        projects = engine_projects.load_projects()
        if projects:
            self.project_var.set(projects[0]['name'])
            self.on_project_select()
        
        self.periodic_git_refresh()

    def _load_full_config(self):
        cfg_path = os.path.join(os.path.dirname(__file__), "orchestrator_config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, 'r') as f: return json.load(f)
        return {}

    def _save_ui_config(self):
        cfg_path = os.path.join(os.path.dirname(__file__), "orchestrator_config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, 'r') as f: full_cfg = json.load(f)
            if "ui" not in full_cfg: full_cfg["ui"] = {}
            full_cfg["ui"]["orch_geometry"] = self.root.geometry()
            with open(cfg_path, 'w') as f: json.dump(full_cfg, f, indent=4)

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background="#1e1e1e")
        self.style.configure("TLabel", background="#1e1e1e", foreground="#d4d4d4", font=("Segoe UI", 9))
        self.style.configure("TButton", padding=3, font=("Segoe UI", 9))
        self.style.configure("Header.TFrame", background="#2d2d2d")
        self.style.configure("Header.TLabel", background="#2d2d2d", font=("Segoe UI", 9, "bold"))
        self.style.configure("Info.TLabel", background="#1e1e1e", foreground="#569cd6", font=("Segoe UI", 9, "italic"))
        self.style.configure("TLabelframe", background="#1e1e1e", foreground="#007acc", font=("Segoe UI", 9, "bold"))
        self.style.configure("TLabelframe.Label", background="#1e1e1e", foreground="#007acc")

    def setup_ui(self):
        self.main_container = ttk.Frame(self.root, padding="15")
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # --- PROJECT BAR ---
        proj_bar = ttk.Frame(self.main_container, style="Header.TFrame", padding="10")
        proj_bar.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(proj_bar, text="Project:", style="Header.TLabel").pack(side=tk.LEFT, padx=(0, 5))
        self.project_var = tk.StringVar()
        self.project_dropdown = ttk.Combobox(proj_bar, textvariable=self.project_var, state="readonly", width=30)
        self.project_dropdown['values'] = [p['name'] for p in engine_projects.load_projects()]
        self.project_dropdown.pack(side=tk.LEFT, padx=5)
        self.project_dropdown.bind("<<ComboboxSelected>>", self.on_project_select)

        ttk.Button(proj_bar, text="+ Add", command=self.open_add_project_popup).pack(side=tk.LEFT, padx=10)
        ttk.Button(proj_bar, text="Manage", command=self.open_edit_projects_popup).pack(side=tk.LEFT)

        # --- INFO PANEL ---
        info_frame = ttk.Frame(self.main_container, padding="5")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        self.git_label = ttk.Label(info_frame, text="Git: --", style="Info.TLabel")
        self.git_label.pack(side=tk.LEFT, padx=(0, 20))
        self.kanban_label = ttk.Label(info_frame, text="Kanban: --", style="Info.TLabel")
        self.kanban_label.pack(side=tk.LEFT)

        # --- ORCHESTRATION ---
        worker_bar = ttk.LabelFrame(self.main_container, text=" Agent Control ", padding="10")
        worker_bar.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(worker_bar, text="Role:").pack(side=tk.LEFT, padx=(0, 5))
        self.role_var = tk.StringVar()
        self.role_dropdown = ttk.Combobox(worker_bar, textvariable=self.role_var, state="readonly", width=15)
        self.role_dropdown['values'] = engine_projects.get_roles()
        if self.role_dropdown['values']: self.role_dropdown.current(0)
        self.role_dropdown.pack(side=tk.LEFT, padx=5)
        ttk.Button(worker_bar, text="Spawn Worker", command=self.start_worker).pack(side=tk.LEFT, padx=15)

        # --- MIRROR HEADER ---
        mirror_bar = ttk.Frame(self.main_container, style="Header.TFrame", padding="5")
        mirror_bar.pack(fill=tk.X, pady=(5, 5))
        self.status_icon = tk.Label(mirror_bar, text="●", fg="red", bg="#2d2d2d", font=("Segoe UI", 11))
        self.status_icon.pack(side=tk.LEFT)
        self.status_label = ttk.Label(mirror_bar, text="Disconnected", style="Header.TLabel")
        self.status_label.pack(side=tk.LEFT, padx=(2, 15))
        self.auto_sync_var = tk.BooleanVar(value=True)
        tk.Checkbutton(mirror_bar, text="Mirroring", variable=self.auto_sync_var, bg="#2d2d2d", fg="#d4d4d4", 
                       selectcolor="#1e1e1e", activebackground="#2d2d2d", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=5)
        self.output_visible = tk.BooleanVar(value=False)
        self.toggle_output_btn = ttk.Button(mirror_bar, text="▼ Show Live", command=self.toggle_output_panel)
        self.toggle_output_btn.pack(side=tk.RIGHT, padx=5)

        # --- TERMINAL MIRROR ---
        self.display_frame = ttk.LabelFrame(self.main_container, text=" Terminal Mirror ", padding="5")
        self.terminal_display = scrolledtext.ScrolledText(
            self.display_frame, state='disabled', bg="#000000", fg="#d4d4d4", font=("Consolas", 10),
            padx=10, pady=10, borderwidth=0, highlightthickness=0
        )
        self.terminal_display.pack(fill=tk.BOTH, expand=True)

        # --- COMMAND FIELD ---
        self.cmd_frame = ttk.LabelFrame(self.main_container, text=" Send Command ", padding="10")
        self.cmd_frame.pack(fill=tk.X, side=tk.TOP, pady=(5, 0))
        self.cmd_entry = ttk.Entry(self.cmd_frame)
        self.cmd_entry.pack(fill=tk.X, expand=True, padx=5)
        self.cmd_entry.bind("<Return>", self.send_command)

    def on_project_select(self, event=None):
        name = self.project_var.get()
        projects = engine_projects.load_projects()
        self.active_project = next((p for p in projects if p['name'] == name), None)
        if self.active_project:
            branch, status, _, _, _ = engine_projects.get_git_info(self.active_project['local_path'])
            self.git_label.config(text=f"Git: [{branch}] {status}")
            self.kanban_label.config(text=f"Kanban: {self.active_project['kanban_project_name']}")

    def periodic_git_refresh(self):
        if self.active_project: self.on_project_select()
        ms = self.full_config.get("terminal", {}).get("git_refresh_ms", 3000)
        self.root.after(ms, self.periodic_git_refresh)

    def open_add_project_popup(self):
        folder = filedialog.askdirectory(initialdir=os.getcwd(), title="Select Project Folder")
        if not folder: return
        popup = tk.Toplevel(self.root); popup.title("Project Details"); popup.geometry("500x300")
        popup.configure(bg="#1e1e1e"); popup.transient(self.root); popup.grab_set()
        frame = ttk.Frame(popup, padding="20"); frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Name (Alias):").pack(fill=tk.X)
        name_entry = ttk.Entry(frame); name_entry.insert(0, os.path.basename(folder)); name_entry.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(frame, text="Kanban Project Name:").pack(fill=tk.X)
        kanban_entry = ttk.Entry(frame); kanban_entry.insert(0, name_entry.get()); kanban_entry.pack(fill=tk.X, pady=(0, 20))
        def on_save():
            if name_entry.get() and kanban_entry.get():
                engine_projects.add_project(name_entry.get(), folder, kanban_entry.get())
                self.project_dropdown['values'] = [prj['name'] for prj in engine_projects.load_projects()]
                self.project_var.set(name_entry.get()); self.on_project_select(); popup.destroy()
        ttk.Button(frame, text="Save Project", command=on_save).pack()

    def open_edit_projects_popup(self):
        popup = tk.Toplevel(self.root); popup.title("Manage Projects"); popup.geometry("1100x500")
        popup.configure(bg="#1e1e1e"); popup.transient(self.root); popup.grab_set()
        main_frame = ttk.Frame(popup, padding="15"); main_frame.pack(fill=tk.BOTH, expand=True)
        cols = ("name", "path", "kanban", "repo", "branch", "commit")
        tree = ttk.Treeview(main_frame, columns=cols, show="headings")
        tree.tag_configure("link", foreground="#569cd6")
        for c in cols: tree.heading(c, text=c.capitalize()); tree.column(c, width=150)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        links = {}
        def refresh():
            for i in tree.get_children(): tree.delete(i)
            for p in engine_projects.load_projects():
                b, s, r, c, rem = engine_projects.get_git_info(p['local_path'])
                iid = tree.insert("", tk.END, values=(p['name'], p['local_path'], p['kanban_project_name'], os.path.basename(r) if r else "N/A", f"{b} ({s})", c), tags=("link",))
                links[(iid, "path")] = p['local_path']
                if rem: links[(iid, "repo")] = rem
                if rem and c: links[(iid, "commit")] = f"{rem}/commit/{c}"
        def on_db(e):
            col = tree.identify_column(e.x); row = tree.identify_row(e.y)
            if row and col:
                c_name = cols[int(col[1:])-1]; l = links.get((row, c_name))
                if l: webbrowser.open(l) if l.startswith("http") else os.startfile(l)
        tree.bind("<Double-Button-1>", on_db); refresh()
        def on_del():
            sel = tree.selection()
            if sel:
                name = tree.item(sel[0])['values'][0]
                if messagebox.askyesno("Delete", f"Remove {name}?"):
                    engine_projects.delete_project(name)
                    self.project_dropdown['values'] = [prj['name'] for prj in engine_projects.load_projects()]
                    refresh()
        ttk.Button(popup, text="Remove Selected", command=on_del).pack(side=tk.RIGHT, padx=15, pady=10)

    def start_worker(self):
        if not self.active_project: return
        title, pid = engine_projects.launch_worker(self.active_project, self.role_var.get())
        
        # Auto-connect mirror after a short delay
        if pid:
            self.root.after(1500, lambda: self.connect_by_pid(pid, title))
        else:
            self.root.after(1500, lambda: self.connect_by_title(title))

    def connect_by_pid(self, target_pid, fallback_title):
        import win32process
        found_h = None
        
        def enum_handler(hwnd, ctx):
            nonlocal found_h
            if win32gui.IsWindowVisible(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == target_pid:
                    found_h = hwnd

        win32gui.EnumWindows(enum_handler, None)
        if found_h:
            self.connect_to_hwnd(found_h, fallback_title)
        else:
            # Fallback to title search
            self.connect_by_title(fallback_title)

    def connect_by_title(self, title):
        for t, h in self.terminal.get_window_list():
            if title.lower() in t.lower(): self.connect_to_hwnd(h, t); return

    def connect_to_hwnd(self, hwnd, title):
        if self.terminal.connect(hwnd, title):
            self.status_icon.config(fg="green"); self.status_label.config(text=f"Mirroring: {title[:20]}...")
            if not self.is_syncing: self.is_syncing = True; self.periodic_sync()

    def toggle_connection(self):
        if self.terminal.connected_hwnd:
            self.terminal.disconnect(); self.status_icon.config(fg="red"); self.status_label.config(text="Disconnected")
        else:
            last = self.full_config.get("terminal", {}).get("last_title")
            if last: self.connect_by_title(last)

    def toggle_output_panel(self):
        if self.output_visible.get():
            self.display_frame.pack_forget(); self.toggle_output_btn.config(text="▼ Show Live"); self.output_visible.set(False)
        else:
            self.cmd_frame.pack_forget(); self.display_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP, pady=5)
            self.cmd_frame.pack(fill=tk.X, side=tk.TOP, pady=(5, 0)); self.toggle_output_btn.config(text="▲ Hide Live"); self.output_visible.set(True)

    def update_sync_interval(self, event=None):
        try:
            v = int(self.sync_val_var.get())
            engine_terminal.save_config({"sync_interval_ms": v})
        except: pass

    def toggle_auto_sync(self): engine_terminal.save_config({"auto_sync": self.auto_sync_var.get()})

    def periodic_sync(self):
        if self.auto_sync_var.get() and self.terminal.connected_title:
            threading.Thread(target=self._uia_sync_thread, daemon=True).start()
        ms = engine_terminal.load_config().get('sync_interval_ms', 1000)
        self.root.after(ms, self.periodic_sync)

    def _uia_sync_thread(self):
        content = self.terminal.get_buffer_text()
        if content: self.root.after(0, self.update_display, content)

    def update_display(self, content):
        self.terminal_display.config(state='normal'); self.terminal_display.delete('1.0', tk.END)
        self.terminal_display.insert(tk.END, content); self.terminal_display.see(tk.END); self.terminal_display.config(state='disabled')

    def send_command(self, event=None):
        cmd = self.cmd_entry.get()
        if cmd and self.terminal.send_command(cmd): self.cmd_entry.delete(0, tk.END); self.root.focus_force()

    def on_closing(self):
        self._save_ui_config(); self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk(); app = OrchestratorUI(root); root.mainloop()
