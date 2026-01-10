import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import os
import json
import webbrowser
import time
import win32gui
import win32process
import win32api
import engine_terminal
import engine_kanban
import engine_projects
import engine_events

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text: return
        x, y, _, cy = self.widget.bbox("insert") if hasattr(self.widget, "bbox") and self.widget.bbox("insert") else (0,0,0,0)
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT, background="#2d2d2d", foreground="#d4d4d4",
                      relief=tk.SOLID, borderwidth=1, font=("Segoe UI", "9", "normal"), padx=5, pady=3)
        label.pack()

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw: tw.destroy()

class OrchestratorUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Project Orchestrator v3")
        
        # Load main config for UI state
        self.full_config = self._load_full_config()
        
        # --- VISIBILITY CHECK ---
        geom = self.full_config.get("ui", {}).get("orch_geometry", "1200x750+50+50")
        try:
            # Parse 1200x750+X+Y
            parts = geom.replace('x', '+').split('+')
            w, h = int(parts[0]), int(parts[1])
            x, y = int(parts[2]), int(parts[3])
            
            # Check if the top-left corner is on any monitor
            if not win32api.MonitorFromPoint((x, y), 0):
                geom = f"{w}x{h}+50+50"
        except:
            geom = "1200x750+50+50"

        self.root.geometry(geom)
        self.root.configure(bg="#1e1e1e")
        
        self.terminal = engine_terminal.TerminalEngine()
        self.is_syncing = False
        self.active_project = None
        self.workers = [] 
        
        # --- BACKGROUND STATUS TRACKING ---
        self.status_lock = threading.Lock()
        self.project_status_cache = {} # name -> git_info_dict
        self.worker_status_cache = [] # List of elapsed time strings
        self.is_running = True
        threading.Thread(target=self._background_status_loop, daemon=True).start()
        
        self.setup_styles()
        self.setup_ui()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.refresh_project_table()
        self.periodic_git_refresh()

    def _get_config_path(self):
        cfg_path = os.path.join(os.path.dirname(__file__), "orchestrator_config.json")
        template_path = os.path.join(os.path.dirname(__file__), "orchestrator_config.template.json")
        if not os.path.exists(cfg_path) and os.path.exists(template_path):
            import shutil
            shutil.copy(template_path, cfg_path)
        return cfg_path

    def _load_full_config(self):
        cfg_path = self._get_config_path()
        if os.path.exists(cfg_path):
            with open(cfg_path, 'r') as f: return json.load(f)
        return {}

    def _save_full_config(self):
        cfg_path = self._get_config_path()
        with open(cfg_path, 'w') as f: json.dump(self.full_config, f, indent=4)

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background="#1e1e1e")
        self.style.configure("TLabel", background="#1e1e1e", foreground="#d4d4d4", font=("Segoe UI", 9))
        self.style.configure("TButton", padding=(5, 1), font=("Segoe UI", 9), borderwidth=1, relief="flat")
        self.style.configure("Header.TFrame", background="#2d2d2d")
        self.style.configure("Header.TLabel", background="#2d2d2d", font=("Segoe UI", 9, "bold"))
        self.style.configure("Info.TLabel", background="#2d2d2d", foreground="#569cd6", font=("Segoe UI", 9, "italic"))
        self.style.configure("TLabelframe", background="#1e1e1e", foreground="#007acc", font=("Segoe UI", 9, "bold"))
        self.style.configure("TLabelframe.Label", background="#1e1e1e", foreground="#007acc")

    def setup_ui(self):
        # --- WINDOW MENU BAR ---
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Settings", command=self.open_settings_popup)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)

        self.main_container = ttk.Frame(self.root, padding="15")
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # --- CONSOLIDATED PROJECT & STATUS BAR ---
        proj_bar = ttk.Frame(self.main_container, style="Header.TFrame", padding="10")
        proj_bar.pack(fill=tk.X, pady=(0, 10))

        # --- PROJECT REGISTRY SECTION ---
        self.proj_sect = ttk.Frame(self.main_container)
        self.proj_sect.pack(fill=tk.X, pady=(0, 5))
        
        proj_header_frame = ttk.Frame(self.proj_sect)
        proj_header_frame.pack(fill=tk.X)
        
        self.proj_fold_btn = ttk.Button(proj_header_frame, text="-", width=3, command=self.toggle_projects)
        self.proj_fold_btn.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(proj_header_frame, text="Project Registry", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)

        self.proj_content_frame = ttk.Frame(self.proj_sect, padding="5")
        self.proj_content_frame.pack(fill=tk.X)

        proj_btns = ttk.Frame(self.proj_content_frame)
        proj_btns.pack(side=tk.RIGHT, padx=5)

        btn_add_proj = ttk.Button(proj_btns, text="+ Add Project", command=self.open_add_project_popup)
        btn_add_proj.pack(fill=tk.X, pady=2)
        ToolTip(btn_add_proj, "Register a new Git repository folder.")

        btn_del_proj = ttk.Button(proj_btns, text="- Remove Project", command=self.delete_selected_project)
        btn_del_proj.pack(fill=tk.X, pady=2)
        ToolTip(btn_del_proj, "Delete the selected project from registry.")

        p_cols = ("name", "path", "kanban", "repo", "branch", "status")
        self.project_tree = ttk.Treeview(self.proj_content_frame, columns=p_cols, show="headings", height=1)
        self.project_tree.tag_configure("link", foreground="#569cd6")
        for c in p_cols: 
            self.project_tree.heading(c, text=c.capitalize())
            self.project_tree.column(c, width=120)
        self.project_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.project_links = {}
        self.project_tree.bind("<Double-Button-1>", self.on_project_double_click)

        # --- WORKER TRACKING SECTION ---
        self.worker_sect = ttk.Frame(self.main_container)
        self.worker_sect.pack(fill=tk.X, pady=(0, 5))
        
        worker_header = ttk.Frame(self.worker_sect)
        worker_header.pack(fill=tk.X)
        
        self.worker_fold_btn = ttk.Button(worker_header, text="-", width=3, command=self.toggle_workers)
        self.worker_fold_btn.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(worker_header, text="Active Workers", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)

        self.worker_content = ttk.Frame(self.worker_sect, padding="5")
        self.worker_content.pack(fill=tk.X)
        
        worker_btns = ttk.Frame(self.worker_content)
        worker_btns.pack(side=tk.RIGHT, padx=5)
        
        btn_create = ttk.Button(worker_btns, text="Create", command=self.open_spawn_worker_popup)
        btn_create.pack(fill=tk.X, pady=2)
        ToolTip(btn_create, "Spawn a new agent terminal for a project.")

        btn_kill = ttk.Button(worker_btns, text="Kill", command=self.kill_selected_worker)
        btn_kill.pack(fill=tk.X, pady=2)
        ToolTip(btn_kill, "Terminate the process and remove from monitoring.")

        btn_connect = ttk.Button(worker_btns, text="Connect", command=self.open_connect_worker_popup)
        btn_connect.pack(fill=tk.X, pady=2)
        ToolTip(btn_connect, "Add an existing terminal window to the monitoring list.")

        btn_disconnect = ttk.Button(worker_btns, text="Disconnect", command=self.remove_selected_worker)
        btn_disconnect.pack(fill=tk.X, pady=2)
        ToolTip(btn_disconnect, "Stop monitoring without killing the process.")

        cols = ("role", "folder", "kanban", "time", "terminal")
        self.worker_tree = ttk.Treeview(self.worker_content, columns=cols, show="headings", height=1)
        self.worker_tree.heading("role", text="Role")
        self.worker_tree.heading("folder", text="Project Folder")
        self.worker_tree.heading("kanban", text="Project Kanban")
        self.worker_tree.heading("time", text="Monitor Time")
        self.worker_tree.heading("terminal", text="Terminal")
        
        for c in cols: self.worker_tree.column(c, width=100)
        self.worker_tree.column("folder", width=250)
        self.worker_tree.column("kanban", width=150)
        self.worker_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.worker_tree.bind("<<TreeviewSelect>>", self.on_worker_select)

        # --- MIRROR SECTION ---
        self.mirror_sect = ttk.Frame(self.main_container)
        self.mirror_sect.pack(fill=tk.BOTH, expand=True, pady=(5, 5))

        self.mirror_header = ttk.Frame(self.mirror_sect, style="Header.TFrame", padding="5")
        self.mirror_header.pack(fill=tk.X)
        
        self.mirror_fold_btn = ttk.Button(self.mirror_header, text="-", width=3, command=self.toggle_output_panel)
        self.mirror_fold_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.status_icon = tk.Label(self.mirror_header, text="●", fg="red", bg="#2d2d2d", font=("Segoe UI", 11))
        self.status_icon.pack(side=tk.LEFT)
        self.status_label = ttk.Label(self.mirror_header, text="Disconnected", style="Header.TLabel")
        self.status_label.pack(side=tk.LEFT, padx=(2, 15))
        
        self.auto_sync_var = tk.BooleanVar(value=True)
        chk_mirror = tk.Checkbutton(self.mirror_header, text="Mirroring", variable=self.auto_sync_var, bg="#2d2d2d", fg="#d4d4d4", 
                       selectcolor="#1e1e1e", activebackground="#2d2d2d", font=("Segoe UI", 9), command=self.toggle_auto_sync)
        chk_mirror.pack(side=tk.LEFT, padx=5)
        ToolTip(chk_mirror, "Enable/Disable background UIA text capture for the terminal.")

        # --- TERMINAL MIRROR & COMMAND ---
        self.output_visible = tk.BooleanVar(value=self.full_config.get("ui", {}).get("show_terminal", True))
        self.display_frame = ttk.Frame(self.mirror_sect, padding="5")
        if self.output_visible.get():
            self.display_frame.pack(fill=tk.BOTH, expand=True)
        else:
            self.mirror_fold_btn.config(text="+")

        # --- COMMAND FIELD (Compact, inside mirror) ---
        self.cmd_frame = ttk.Frame(self.display_frame, padding="5")
        self.cmd_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Label(self.cmd_frame, text="Send Command:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(5, 5))
        self.cmd_entry = ttk.Entry(self.cmd_frame)
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.cmd_entry.bind("<Return>", self.send_command)
        ToolTip(self.cmd_entry, "Type a command and press Enter to send it directly to the connected agent terminal.")
        
        self.terminal_display = scrolledtext.ScrolledText(
            self.display_frame, state='disabled', bg="#000000", fg="#d4d4d4", font=("Consolas", 10),
            padx=10, pady=10, borderwidth=0, highlightthickness=0
        )
        self.terminal_display.pack(fill=tk.BOTH, expand=True)

    def _center_popup(self, popup, width, height):
        self.root.update_idletasks()
        px = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - (width // 2)
        py = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - (height // 2)
        popup.geometry(f"{width}x{height}+{px}+{py}")
        popup.transient(self.root)
        popup.grab_set()

    def open_spawn_worker_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Create Worker")
        self._center_popup(popup, 500, 400)
        
        frame = ttk.Frame(popup, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Project Selection
        ttk.Label(frame, text="Select Project:", font=("Segoe UI", 9, "bold")).pack(fill=tk.X, pady=(0, 5))
        projects = engine_projects.load_projects()
        project_names = [p['name'] for p in projects]
        
        proj_var = tk.StringVar()
        proj_dropdown = ttk.Combobox(frame, textvariable=proj_var, values=project_names, state="readonly")
        if project_names: proj_dropdown.current(0)
        proj_dropdown.pack(fill=tk.X, pady=(0, 15))
        
        # Role Selection
        ttk.Label(frame, text="Select Role:", font=("Segoe UI", 9, "bold")).pack(fill=tk.X, pady=(0, 5))
        roles = engine_projects.get_roles()
        role_var = tk.StringVar()
        role_dropdown = ttk.Combobox(frame, textvariable=role_var, values=roles, state="readonly")
        if roles: role_dropdown.current(0)
        role_dropdown.pack(fill=tk.X, pady=(0, 20))
        
        def on_spawn():
            p_name = proj_var.get()
            selected_proj = next((p for p in projects if p['name'] == p_name), None)
            if not selected_proj: return
            
            role = role_var.get()
            title, pid = engine_projects.launch_worker(selected_proj, role)
            
            worker_info = {
                "role": role,
                "folder": selected_proj['local_path'],
                "kanban": selected_proj['kanban_project_name'],
                "start_time": time.time(),
                "terminal": title,
                "pid": pid,
                "runtime_id": None
            }
            with self.status_lock:
                self.workers.append(worker_info)
            self.refresh_worker_table()

            if pid: self.root.after(1500, lambda: self.connect_by_pid(pid, title))
            else: self.root.after(1500, lambda: self.connect_by_title(title))
            popup.destroy()

        ttk.Button(frame, text="Create Worker", command=on_spawn).pack(pady=10)

    def open_connect_worker_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Connect Existing Terminal")
        self._center_popup(popup, 600, 500)
        
        frame = ttk.Frame(popup, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # 1. Terminal Window Selection
        ttk.Label(frame, text="1. Select Existing Window:", font=("Segoe UI", 9, "bold")).pack(fill=tk.X, pady=(0, 5))
        windows = self.terminal.get_window_list()
        win_map = { f"{t} (HWND: {h}, ID: {rid[:10]}...)": (t, h, rid) for t, h, rid in windows }
        win_titles = sorted(list(win_map.keys()))
        
        win_var = tk.StringVar()
        win_dropdown = ttk.Combobox(frame, textvariable=win_var, values=win_titles, state="readonly")
        if win_titles: win_dropdown.current(0)
        win_dropdown.pack(fill=tk.X, pady=(0, 15))

        # 2. Project Selection
        ttk.Label(frame, text="2. Associate with Project:", font=("Segoe UI", 9, "bold")).pack(fill=tk.X, pady=(0, 5))
        projects = engine_projects.load_projects()
        
        proj_var = tk.StringVar()
        proj_dropdown = ttk.Combobox(frame, textvariable=proj_var, state="readonly")
        proj_dropdown.pack(fill=tk.X, pady=(0, 15))

        # 3. Role Selection
        ttk.Label(frame, text="3. Associate with Role:", font=("Segoe UI", 9, "bold")).pack(fill=tk.X, pady=(0, 5))
        roles = ["?"] + engine_projects.get_roles()
        role_var = tk.StringVar(value="?")
        role_dropdown = ttk.Combobox(frame, textvariable=role_var, values=roles, state="readonly")
        role_dropdown.pack(fill=tk.X, pady=(0, 20))

        def update_project_list(*args):
            if not win_var.get(): return
            _, hwnd, _ = win_map[win_var.get()]
            cwd = self.terminal.get_process_cwd(hwnd)
            
            filtered_names = ["None"]
            suggested_idx = 0
            
            if cwd:
                # Find projects that are subpaths or roots of this CWD
                norm_cwd = os.path.normpath(cwd).lower()
                for p in projects:
                    p_path = os.path.normpath(p['local_path']).lower()
                    if norm_cwd.startswith(p_path) or p_path.startswith(norm_cwd):
                        filtered_names.append(p['name'])
                        suggested_idx = len(filtered_names) - 1
            else:
                filtered_names.extend([p['name'] for p in projects])

            proj_dropdown['values'] = filtered_names
            proj_dropdown.current(suggested_idx)

        win_var.trace_add("write", update_project_list)
        update_project_list() # Initial trigger

        def on_connect():
            if not win_var.get() or not proj_var.get(): return
            
            title, hwnd, rid = win_map[win_var.get()]
            p_name = proj_var.get()
            selected_proj = next((p for p in projects if p['name'] == p_name), None)
            role = role_var.get()

            worker_info = {
                "role": role,
                "folder": selected_proj['local_path'] if selected_proj else "N/A",
                "kanban": selected_proj['kanban_project_name'] if selected_proj else "None",
                "start_time": time.time(),
                "terminal": title,
                "runtime_id": rid,
                "hwnd": hwnd,
                "pid": None # Manually connected
            }
            with self.status_lock:
                self.workers.append(worker_info)
            
            self.refresh_worker_table()
            self.connect_to_hwnd(hwnd, title, rid)
            popup.destroy()

        ttk.Button(frame, text="Add to Monitoring", command=on_connect).pack(pady=10)

    def kill_selected_worker(self):
        sel = self.worker_tree.selection()
        if not sel: return
        
        item_idx = self.worker_tree.index(sel[0])
        worker_to_kill = None
        
        with self.status_lock:
            if 0 <= item_idx < len(self.workers):
                worker_to_kill = self.workers[item_idx]

        if not worker_to_kill: return

        confirmed = False
        if worker_to_kill.get('pid'):
            if messagebox.askyesno("Kill Process", f"Are you sure you want to terminate {worker_to_kill['terminal']} (PID: {worker_to_kill['pid']})?"):
                engine_projects.kill_process(worker_to_kill['pid'])
                confirmed = True
        else:
            if messagebox.askyesno("Remove", "No PID found for this worker. Just remove from list?"):
                confirmed = True

        if confirmed:
            with self.status_lock:
                # Re-verify index in case list changed during prompt
                if 0 <= item_idx < len(self.workers) and self.workers[item_idx] == worker_to_kill:
                    self.workers.pop(item_idx)
                else:
                    # Fallback: find by identity if index shifted
                    if worker_to_kill in self.workers:
                        self.workers.remove(worker_to_kill)
            self.refresh_worker_table()

    def on_project_select(self, event=None):
        pass

    def _background_status_loop(self):
        """Heavy lifting (Git/API) happens here in a separate thread."""
        while self.is_running:
            try:
                # 1. Update Project Statuses
                projects = engine_projects.load_projects()
                new_project_cache = {}
                for p in projects:
                    git_info = engine_projects.get_git_info(p['local_path'])
                    kb_url = engine_projects.get_kanban_url(p['kanban_project_name'])
                    new_project_cache[p['name']] = {
                        "git": git_info, # (branch, status, root, commit, remote)
                        "kanban_url": kb_url,
                        "data": p
                    }

                # 2. Update Worker Times
                new_worker_times = []
                with self.status_lock:
                    current_workers = list(self.workers)
                
                for w in current_workers:
                    elapsed = int(time.time() - w['start_time'])
                    mins, secs = divmod(elapsed, 60)
                    new_worker_times.append(f"{mins}m {secs}s")

                # 3. Commit to cache
                with self.status_lock:
                    self.project_status_cache = new_project_cache
                    self.worker_status_cache = new_worker_times
            except Exception as e:
                print(f"[Status Thread Error] {e}")
            
            # Sleep based on config
            ms = self.full_config.get("terminal", {}).get("git_refresh_ms", 3000)
            time.sleep(ms / 1000.0)

    def periodic_git_refresh(self):
        """UI Tick: Just renders the latest cached data."""
        self.refresh_worker_table()
        self.refresh_project_table()
        self.root.after(500, self.periodic_git_refresh) # Faster UI response, but heavy work is throttled by thread

    def open_add_project_popup(self):
        folder = filedialog.askdirectory(initialdir=os.getcwd(), title="Select Project Folder")
        if not folder: return
        popup = tk.Toplevel(self.root); popup.title("Project Details")
        self._center_popup(popup, 500, 300)
        frame = ttk.Frame(popup, padding="20"); frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Name (Alias):").pack(fill=tk.X)
        name_entry = ttk.Entry(frame); name_entry.insert(0, os.path.basename(folder)); name_entry.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(frame, text="Kanban Project Name:").pack(fill=tk.X)
        kanban_entry = ttk.Entry(frame); kanban_entry.insert(0, name_entry.get()); kanban_entry.pack(fill=tk.X, pady=(0, 20))
        def on_save():
            if name_entry.get() and kanban_entry.get():
                engine_projects.add_project(name_entry.get(), folder, kanban_project_name=kanban_entry.get())
                self.refresh_project_table()
                popup.destroy()
        ttk.Button(frame, text="Save Project", command=on_save).pack()

    def remove_selected_worker(self):
        sel = self.worker_tree.selection()
        if sel:
            item_idx = self.worker_tree.index(sel[0])
            if messagebox.askyesno("Disconnect", "Stop monitoring this worker? (The process will keep running)"):
                with self.status_lock:
                    if 0 <= item_idx < len(self.workers):
                        self.workers.pop(item_idx)
                self.refresh_worker_table()

    def refresh_project_table(self):
        with self.status_lock:
            cache = dict(self.project_status_cache)
        
        # Save selection
        selected_name = None
        sel = self.project_tree.selection()
        if sel:
            selected_name = self.project_tree.item(sel[0])['values'][0]

        self.project_links = {}
        for i in self.project_tree.get_children(): self.project_tree.delete(i)
        
        to_select = None
        for name, info in cache.items():
            p = info['data']
            b, s, r, c, rem = info['git']
            iid = self.project_tree.insert("", tk.END, values=(
                p['name'], p['local_path'], p['kanban_project_name'], 
                os.path.basename(r) if r else "N/A", b, s
            ), tags=("link",))
            
            if p['name'] == selected_name:
                to_select = iid

            self.project_links[(iid, "path")] = p['local_path']
            self.project_links[(iid, "kanban")] = info['kanban_url']
            if rem: self.project_links[(iid, "repo")] = rem
        
        if to_select:
            self.project_tree.selection_set(to_select)

        max_h = self.full_config.get("ui", {}).get("table_max_height", 6)
        new_h = min(max_h, len(cache) + 1)
        self.project_tree.config(height=max_h if len(cache) >= max_h else new_h)

    def on_project_double_click(self, event):
        col = self.project_tree.identify_column(event.x)
        row = self.project_tree.identify_row(event.y)
        if row and col:
            cols = ("name", "path", "kanban", "repo", "branch", "status")
            c_name = cols[int(col[1:])-1]
            l = self.project_links.get((row, c_name))
            if l: webbrowser.open(l) if l.startswith("http") else os.startfile(l)

    def delete_selected_project(self):
        sel = self.project_tree.selection()
        if sel:
            name = self.project_tree.item(sel[0])['values'][0]
            if messagebox.askyesno("Delete", f"Remove {name}?"):
                engine_projects.delete_project(name)
                self.refresh_project_table()

    def open_settings_popup(self):
        popup = tk.Toplevel(self.root); popup.title("Global Settings")
        self._center_popup(popup, 500, 750)
        main = ttk.Frame(popup, padding=20); main.pack(fill=tk.BOTH, expand=True)
        
        descriptions = {
            "ip": "The IP address of the Kanban server.",
            "port": "The network port for the Kanban API connection.",
            "last_project": "The project that will be selected by default on startup.",
            "last_user": "The default user to monitor in the Kanban board.",
            "poll_interval": "Seconds between Kanban API update checks.",
            "sync_interval_ms": "Milliseconds between terminal screen captures.",
            "auto_sync": "Enable background capturing of terminal text.",
            "last_title": "Window title of the last connected agent terminal.",
            "last_geometry": "Saved window size/position of the agent terminal.",
            "git_refresh_ms": "Milliseconds between Git status and branch checks.",
            "orch_geometry": "The Orchestrator's own window size and screen coordinates.",
            "show_terminal": "Determines if the Live Terminal Mirror is visible on startup.",
            "table_max_height": "Maximum rows to display in UI tables before scrolling."
        }

        sections = ["kanban", "terminal", "ui"]
        entries = {}
        for section in sections:
            ttk.Label(main, text=f"[{section.upper()}]", font=("Segoe UI", 10, "bold")).pack(fill=tk.X, pady=(10, 5))
            for key, val in self.full_config.get(section, {}).items():
                if isinstance(val, (str, int, float, bool)):
                    f = ttk.Frame(main); f.pack(fill=tk.X, pady=2)
                    label_text = key
                    if key == "poll_interval": label_text = "poll_interval (s)"
                    if key == "sync_interval_ms": label_text = "sync_interval (ms)"
                    
                    lbl = ttk.Label(f, text=f"{label_text}:", width=25)
                    lbl.pack(side=tk.LEFT)
                    if key in descriptions: ToolTip(lbl, descriptions[key])

                    if isinstance(val, bool):
                        w = ttk.Combobox(f, values=["True", "False"], state="readonly")
                        w.set(str(val))
                        w.pack(side=tk.LEFT, fill=tk.X, expand=True)
                    else:
                        w = ttk.Entry(f)
                        w.insert(0, str(val))
                        w.pack(side=tk.LEFT, fill=tk.X, expand=True)
                    
                    entries[(section, key)] = w
        
        def save():
            try:
                for (sec, key), entry in entries.items():
                    orig_val = self.full_config[sec][key]
                    new_val_str = entry.get()
                    if type(orig_val) is bool:
                        new_val = new_val_str.lower() in ("true", "1", "yes")
                    elif isinstance(orig_val, int): new_val = int(new_val_str)
                    elif isinstance(orig_val, float): new_val = float(new_val_str)
                    else: new_val = new_val_str
                    self.full_config[sec][key] = new_val
                self._save_full_config()
                popup.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Invalid value: {e}")
        
        ttk.Button(main, text="Save All", command=save).pack(pady=20)

    def refresh_worker_table(self):
        with self.status_lock:
            workers = list(self.workers)
            times = list(self.worker_status_cache)
            
        # Save selection
        selected_terminal = None
        sel = self.worker_tree.selection()
        if sel:
            selected_terminal = self.worker_tree.item(sel[0])['values'][4] # terminal column

        for i in self.worker_tree.get_children(): self.worker_tree.delete(i)
        
        to_select = None
        for idx, w in enumerate(workers):
            time_str = times[idx] if idx < len(times) else "Calculating..."
            iid = self.worker_tree.insert("", tk.END, values=(w['role'], w['folder'], w['kanban'], time_str, w['terminal']))
            if w['terminal'] == selected_terminal:
                to_select = iid
        
        if to_select:
            self.worker_tree.selection_set(to_select)

        max_h = self.full_config.get("ui", {}).get("table_max_height", 6)
        new_h = min(max_h, len(workers) + 1)
        self.worker_tree.config(height=max_h if len(workers) >= max_h else new_h)

    def connect_by_pid(self, target_pid, fallback_title):
        import win32process
        found_h = None
        def enum_handler(hwnd, ctx):
            nonlocal found_h
            if win32gui.IsWindowVisible(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == target_pid: found_h = hwnd
        win32gui.EnumWindows(enum_handler, None)
        
        if found_h:
            # Try to find specific tab for this HWND to get RID
            rid = None
            for t, h, r in self.terminal.get_window_list():
                if h == found_h and (fallback_title.lower() in t.lower()):
                    rid = r
                    break
            self.connect_to_hwnd(found_h, fallback_title, rid)
        else: self.connect_by_title(fallback_title)

    def connect_by_title(self, title):
        for t, h, rid in self.terminal.get_window_list():
            if title.lower() in t.lower(): self.connect_to_hwnd(h, t, rid); return

    def connect_to_hwnd(self, hwnd, title, rid=None):
        if self.terminal.connect(hwnd, title, rid):
            self.status_icon.config(fg="green"); self.status_label.config(text=f"Mirroring: {title[:20]}...")
            if not self.is_syncing:
                self.is_syncing = True
                threading.Thread(target=self._uia_sync_loop, daemon=True).start()

    def on_worker_select(self, event=None):
        sel = self.worker_tree.selection()
        if not sel: return
        
        item_idx = self.worker_tree.index(sel[0])
        with self.status_lock:
            if 0 <= item_idx < len(self.workers):
                w = self.workers[item_idx]
                # Find HWND and ID from window list if not present
                if not w.get("hwnd"):
                    for title, hwnd, rid in self.terminal.get_window_list():
                        if w["terminal"] == title:
                            w["hwnd"] = hwnd
                            w["runtime_id"] = rid
                            break
                
                if w.get("hwnd"):
                    self.connect_to_hwnd(w["hwnd"], w["terminal"], w.get("runtime_id"))
                    # Immediately show cached buffer
                    if w.get("last_buffer"):
                        self.update_display(w["last_buffer"])

    def toggle_workers(self):
        if self.worker_content.winfo_viewable():
            self.worker_content.pack_forget()
            self.worker_fold_btn.config(text="+")
        else:
            self.worker_content.pack(fill=tk.X)
            self.worker_fold_btn.config(text="-")

    def toggle_projects(self):
        if self.proj_content_frame.winfo_viewable():
            self.proj_content_frame.pack_forget()
            self.proj_fold_btn.config(text="+")
        else:
            self.proj_content_frame.pack(fill=tk.X)
            self.proj_fold_btn.config(text="-")

    def toggle_output_panel(self):
        if self.output_visible.get():
            self.display_frame.pack_forget()
            self.mirror_fold_btn.config(text="+")
            self.output_visible.set(False)
        else:
            self.display_frame.pack(fill=tk.BOTH, expand=True)
            self.mirror_fold_btn.config(text="-")
            self.output_visible.set(True)
        self.full_config["ui"]["show_terminal"] = self.output_visible.get()
        self._save_full_config()

    def toggle_auto_sync(self): 
        self.full_config["terminal"]["auto_sync"] = self.auto_sync_var.get(); self._save_full_config()

    def _uia_sync_loop(self):
        """Persistent background thread for multi-worker mirroring."""
        import time
        while self.is_syncing:
            if not self.auto_sync_var.get():
                time.sleep(1)
                continue

            with self.status_lock:
                current_workers = list(self.workers)

            for w in current_workers:
                try:
                    # 1. Resolve HWND/ID if missing
                    if not w.get("hwnd"):
                        for title, hwnd, rid in self.terminal.get_window_list():
                            if w["terminal"] == title:
                                w["hwnd"] = hwnd
                                w["runtime_id"] = rid
                                break
                    
                    if not w.get("hwnd"): continue

                    # 2. Capture buffer
                    content = self.terminal.get_buffer_text(
                        hwnd=w.get("hwnd"), 
                        title=w["terminal"], 
                        runtime_id=w.get("runtime_id")
                    )

                    if content:
                        w["last_buffer"] = content
                        # 3. If this is the active terminal, update the UI
                        if w.get("hwnd") == self.terminal.connected_hwnd:
                            self.root.after(0, self.update_display, content)
                except Exception as e:
                    print(f"[Sync Loop Error] {e}")

            ms = self.full_config.get("terminal", {}).get('sync_interval_ms', 1000)
            time.sleep(ms / 1000.0)

    def update_display(self, content):
        self.terminal_display.config(state='normal'); self.terminal_display.delete('1.0', tk.END)
        self.terminal_display.insert(tk.END, content); self.terminal_display.see(tk.END); self.terminal_display.config(state='disabled')

    def send_command(self, event=None):
        cmd = self.cmd_entry.get()
        if cmd and self.terminal.send_command(cmd): self.cmd_entry.delete(0, tk.END); self.root.focus_force()

    def on_closing(self):
        self.full_config["ui"]["orch_geometry"] = self.root.geometry()
        self.full_config["ui"]["show_terminal"] = self.output_visible.get()
        self._save_full_config(); self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk(); app = OrchestratorUI(root); root.mainloop()