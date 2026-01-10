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
from manager_projects import ProjectManager
from manager_workers import WorkerManager
import utils_ui
import orchestrator_popups

class OrchestratorUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Project Orchestrator v3")
        
        # Load main config for UI state
        self.full_config = utils_ui.load_full_config()
        
        # --- VISIBILITY CHECK ---
        geom = self.full_config.get("ui", {}).get("orch_geometry", "1200x750+50+50")
        is_maximized = self.full_config.get("ui", {}).get("orch_maximized", False)
        try:
            # Parse 1200x750+X+Y
            parts = geom.replace('x', '+').split('+')
            w, h = int(parts[0]), int(parts[1])
            x, y = int(parts[2]), int(parts[3])
            
            # Check if the coordinates are on any monitor. 
            # We check multiple points (corners) to be sure it's visible.
            monitor_found = False
            for test_x, test_y in [(x+20, y+20), (x+w-20, y+20)]:
                if win32api.MonitorFromPoint((test_x, test_y), 0): # 0 = MONITOR_DEFAULTTONULL
                    monitor_found = True
                    break
            
            if not monitor_found:
                geom = f"{w}x{h}+50+50"
        except:
            geom = "1200x750+50+50"

        self.root.geometry(geom)
        if is_maximized:
            try:
                self.root.update_idletasks() # Ensure position is set before zooming
                self.root.state('zoomed')
            except: pass
        self.root.configure(bg="#1e1e1e")
        
        self.terminal = engine_terminal.TerminalEngine()
        self.active_project = None
        
        # --- MANAGERS ---
        self.projects_mgr = ProjectManager(self.full_config)
        self.workers_mgr = WorkerManager(self.full_config, self.terminal)
        
        # Bind callbacks
        self.projects_mgr.on_update_callback = lambda: self.root.after(0, self.refresh_project_table)
        self.workers_mgr.on_update_callback = lambda: self.root.after(0, self.refresh_worker_table)
        self.workers_mgr.on_buffer_callback = self.on_buffer_update
        
        self.projects_mgr.start()
        self.workers_mgr.start_sync()
        
        self.setup_styles()
        self.setup_ui()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.refresh_project_table()
        self.periodic_refresh()
        
        # --- AUTO RESTORE ---
        saved_setup = self.full_config.get("ui", {}).get("last_worker_setup")
        if saved_setup:
            print(f"[Orchestrator] Restoring {len(saved_setup)} workers from autosave...")
            self.workers_mgr.apply_setup(saved_setup)

    def on_buffer_update(self, hwnd, content):
        if hwnd == self.terminal.connected_hwnd:
            self.root.after(0, self.update_display, content)
        
        # Surgical update of the size column in the treeview
        self.root.after(0, self.update_tree_size, hwnd, len(content))

    def update_tree_size(self, hwnd, size):
        for item in self.worker_tree.get_children():
            values = self.worker_tree.item(item, "values")
            # The ID column (index 0) is "hwnd:rid"
            if values and str(hwnd) in values[0]:
                new_values = list(values)
                # Size is index 6
                new_values[6] = f"{size:,}"
                self.worker_tree.item(item, values=new_values)
                break

    def periodic_refresh(self):
        """UI Tick: Just renders the latest cached data for elapsed times."""
        self.refresh_worker_table()
        self.root.after(1000, self.periodic_refresh)

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
        file_menu.add_command(label="Save Worker Setup", command=self.save_worker_setup)
        file_menu.add_command(label="Load Worker Setup", command=self.load_worker_setup)
        file_menu.add_separator()
        file_menu.add_command(label="Settings", command=lambda: orchestrator_popups.open_settings_popup(self))
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

        btn_add_proj = ttk.Button(proj_btns, text="+ Add Project", command=lambda: orchestrator_popups.open_add_project_popup(self))
        btn_add_proj.pack(fill=tk.X, pady=2)
        utils_ui.ToolTip(btn_add_proj, "Register a new Git repository folder.")

        btn_del_proj = ttk.Button(proj_btns, text="- Remove Project", command=self.delete_selected_project)
        btn_del_proj.pack(fill=tk.X, pady=2)
        utils_ui.ToolTip(btn_del_proj, "Delete the selected project from registry.")

        p_cols = ("id", "path", "kanban", "repo", "branch", "status")
        self.project_tree = ttk.Treeview(self.proj_content_frame, columns=p_cols, show="headings", height=1)
        self.project_tree.tag_configure("link", foreground="#569cd6")
        for c in p_cols: 
            text = "ID" if c == "id" else c.capitalize()
            self.project_tree.heading(c, text=text)
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
        
        btn_create = ttk.Button(worker_btns, text="Create", command=lambda: orchestrator_popups.open_spawn_worker_popup(self))
        btn_create.pack(fill=tk.X, pady=2)
        utils_ui.ToolTip(btn_create, "Spawn a new agent terminal for a project.")

        btn_kill = ttk.Button(worker_btns, text="Kill", command=self.kill_selected_worker)
        btn_kill.pack(fill=tk.X, pady=2)
        utils_ui.ToolTip(btn_kill, "Terminate the process and remove from monitoring.")

        btn_connect = ttk.Button(worker_btns, text="Connect", command=lambda: orchestrator_popups.open_connect_worker_popup(self))
        btn_connect.pack(fill=tk.X, pady=2)
        utils_ui.ToolTip(btn_connect, "Add an existing terminal window to the monitoring list.")

        btn_disconnect = ttk.Button(worker_btns, text="Disconnect", command=self.remove_selected_worker)
        btn_disconnect.pack(fill=tk.X, pady=2)
        utils_ui.ToolTip(btn_disconnect, "Stop monitoring without killing the process.")

        cols = ("id", "name", "status", "role", "folder", "kanban", "size", "time")
        self.worker_tree = ttk.Treeview(self.worker_content, columns=cols, show="headings", height=1)
        self.worker_tree.heading("id", text="ID")
        self.worker_tree.heading("name", text="Name")
        self.worker_tree.heading("status", text="Status")
        self.worker_tree.heading("role", text="Role")
        self.worker_tree.heading("folder", text="Project Folder")
        self.worker_tree.heading("kanban", text="Project Kanban")
        self.worker_tree.heading("size", text="Size (Chr)")
        self.worker_tree.heading("time", text="Monitor Time")
        
        for c in cols: self.worker_tree.column(c, width=100)
        self.worker_tree.column("id", width=80)
        self.worker_tree.column("name", width=120)
        self.worker_tree.column("status", width=180)
        self.worker_tree.column("folder", width=250)
        self.worker_tree.column("kanban", width=150)
        self.worker_tree.column("size", width=80)
        self.worker_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.worker_tree.bind("<<TreeviewSelect>>", self.on_worker_select)
        self.worker_tree.bind("<Double-Button-1>", self.on_worker_double_click)

        # --- MIRROR SECTION ---
        self.mirror_sect = ttk.Frame(self.main_container)
        self.mirror_sect.pack(fill=tk.BOTH, expand=True, pady=(5, 5))

        self.mirror_header = ttk.Frame(self.mirror_sect, style="Header.TFrame", padding="5")
        self.mirror_header.pack(fill=tk.X)
        
        self.mirror_fold_btn = ttk.Button(self.mirror_header, text="-", width=3, command=self.toggle_output_panel)
        self.mirror_fold_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(self.mirror_header, text="Live Terminal Mirror", style="Header.TLabel").pack(side=tk.LEFT, padx=5)

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
        utils_ui.ToolTip(self.cmd_entry, "Type a command and press Enter to send it directly to the connected agent terminal.")
        
        self.terminal_display = scrolledtext.ScrolledText(
            self.display_frame, state='disabled', bg="#000000", fg="#d4d4d4", font=("Consolas", 10),
            padx=10, pady=10, borderwidth=0, highlightthickness=0
        )
        self.terminal_display.pack(fill=tk.BOTH, expand=True)

    def kill_selected_worker(self):
        sel = self.worker_tree.selection()
        if not sel: return
        
        item_idx = self.worker_tree.index(sel[0])
        workers, _ = self.workers_mgr.get_workers()
        
        if 0 <= item_idx < len(workers):
            worker_to_kill = workers[item_idx]
        else: return

        confirmed = False
        if worker_to_kill.get('pid'):
            if messagebox.askyesno("Kill Process", f"Are you sure you want to terminate {worker_to_kill['terminal']} (PID: {worker_to_kill['pid']})?"):
                engine_projects.kill_process(worker_to_kill['pid'])
                confirmed = True
        else:
            if messagebox.askyesno("Remove", "No PID found for this worker. Just remove from list?"):
                confirmed = True

        if confirmed:
            self.workers_mgr.remove_worker(item_idx)
            self.refresh_worker_table()

    def remove_selected_worker(self):
        sel = self.worker_tree.selection()
        if sel:
            item_idx = self.worker_tree.index(sel[0])
            if messagebox.askyesno("Disconnect", "Stop monitoring this worker? (The process will keep running)"):
                self.workers_mgr.remove_worker(item_idx)
                self.refresh_worker_table()

    def refresh_project_table(self):
        cache = self.projects_mgr.get_cache()
        
        # Save selection
        selected_id = None
        sel = self.project_tree.selection()
        if sel:
            selected_id = self.project_tree.item(sel[0])['values'][0]

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
            
            if p['name'] == selected_id:
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
            cols = ("id", "path", "kanban", "repo", "branch", "status")
            c_name = cols[int(col[1:])-1]
            l = self.project_links.get((row, c_name))
            if l: webbrowser.open(l) if l.startswith("http") else os.startfile(l)

    def delete_selected_project(self):
        sel = self.project_tree.selection()
        if sel:
            pid = self.project_tree.item(sel[0])['values'][0]
            if messagebox.askyesno("Delete", f"Remove project {pid}?"):
                engine_projects.delete_project(pid)
                self.refresh_project_table()

    def refresh_worker_table(self):
        workers, times = self.workers_mgr.get_workers()
            
        # Save selection
        selected_id = None
        sel = self.worker_tree.selection()
        if sel:
            selected_id = self.worker_tree.item(sel[0])['values'][0] # ID column

        for i in self.worker_tree.get_children(): self.worker_tree.delete(i)
        
        to_select = None
        for idx, w in enumerate(workers):
            time_str = times[idx] if idx < len(times) else "Calculating..."
            
            # Construct enhanced status
            base_status = w.get('status', '???')
            if base_status == "Online":
                indicator = "[C]" if w.get("is_cached") else "[V]"
                hits = w.get("hits", 0)
                walks = w.get("walks", 0)
                status_str = f"{indicator} {base_status} (H:{hits} V:{walks})"
            else:
                status_str = base_status

            size = len(w.get("last_buffer", ""))
            
            iid = self.worker_tree.insert("", tk.END, values=(
                w.get('id', '???'), 
                w.get('terminal', '???'),
                status_str, 
                w.get('role', '???'), 
                w.get('folder', '???'), 
                w.get('kanban', '???'),
                f"{size:,}",
                time_str
            ))
            if w.get('id') == selected_id:
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
        self.terminal.connect(hwnd, title, rid)

    def on_worker_select(self, event=None):
        sel = self.worker_tree.selection()
        if not sel: return
        
        item_idx = self.worker_tree.index(sel[0])
        workers, _ = self.workers_mgr.get_workers()
        if 0 <= item_idx < len(workers):
            w = workers[item_idx]
            # Manual resolution needs to fetch window list
            if self.workers_mgr._resolve_worker_identity(w, self.terminal.get_window_list()):
                self.root.after(0, self.refresh_worker_table)
            
            if w.get("hwnd"):
                self.connect_to_hwnd(w["hwnd"], w["terminal"], w.get("runtime_id"))
                if w.get("last_buffer"):
                    self.update_display(w["last_buffer"])

    def on_worker_double_click(self, event):
        col = self.worker_tree.identify_column(event.x)
        # ID is #1, Name is #2
        if col in ["#1", "#2"]:
            self.terminal.activate()

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
        utils_ui.save_full_config(self.full_config)


    def update_display(self, content):
        self.terminal_display.config(state='normal'); self.terminal_display.delete('1.0', tk.END)
        self.terminal_display.insert(tk.END, content); self.terminal_display.see(tk.END); self.terminal_display.config(state='disabled')

    def send_command(self, event=None):
        cmd = self.cmd_entry.get()
        if cmd and self.terminal.send_command(cmd): self.cmd_entry.delete(0, tk.END); self.root.focus_force()

    def save_worker_setup(self):
        setup = self.workers_mgr.get_setup()
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if f:
            try:
                with open(f, 'w') as out:
                    json.dump(setup, out, indent=4)
                messagebox.showinfo("Success", f"Worker setup saved to {os.path.basename(f)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save setup: {e}")

    def load_worker_setup(self):
        f = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if f:
            try:
                with open(f, 'r') as infile:
                    setup = json.load(infile)
                self.workers_mgr.apply_setup(setup)
                self.refresh_worker_table()
                messagebox.showinfo("Success", f"Loaded {len(setup)} workers. Monitoring will begin automatically.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load setup: {e}")

    def on_closing(self):
        self.projects_mgr.stop()
        self.workers_mgr.stop_sync()
        
        # Autosave workers
        self.full_config.setdefault("ui", {})["last_worker_setup"] = self.workers_mgr.get_setup()

        # If maximized, save the 'normal' geometry so we can restore it properly
        if self.root.state() == 'zoomed':
            self.full_config["ui"]["orch_geometry"] = self.root.wm_geometry()
            self.full_config["ui"]["orch_maximized"] = True
        else:
            self.full_config["ui"]["orch_geometry"] = self.root.geometry()
            self.full_config["ui"]["orch_maximized"] = False

        self.full_config["ui"]["show_terminal"] = self.output_visible.get()
        utils_ui.save_full_config(self.full_config); self.root.destroy()

if __name__ == "__main__":
    import uiautomation as auto
    with auto.UIAutomationInitializerInThread():
        root = tk.Tk(); app = OrchestratorUI(root); root.mainloop()
