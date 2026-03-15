import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import time
import engine_projects
import utils_ui

def open_spawn_worker_popup(app):
    popup = tk.Toplevel(app.root)
    popup.title("Create Worker")
    utils_ui.center_popup(app.root, popup, 500, 400)
    
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
            "id": "Pending",
            "status": "Starting",
            "role": role,
            "folder": selected_proj['local_path'],
            "kanban": selected_proj['kanban_project_name'],
            "start_time": time.time(),
            "terminal": title,
            "pid": pid,
            "runtime_id": None
        }
        app.workers_mgr.add_worker(worker_info)
        app.refresh_worker_table()

        if pid: app.root.after(1500, lambda: app.connect_by_pid(pid, title))
        else: app.root.after(1500, lambda: app.connect_by_title(title))
        popup.destroy()

    ttk.Button(frame, text="Create Worker", command=on_spawn).pack(pady=10)

def open_connect_worker_popup(app):
    popup = tk.Toplevel(app.root)
    popup.title("Connect Existing Terminal")
    utils_ui.center_popup(app.root, popup, 600, 500)
    
    frame = ttk.Frame(popup, padding="20")
    frame.pack(fill=tk.BOTH, expand=True)

    # 1. Terminal Window Selection
    ttk.Label(frame, text="1. Select Existing Window:", font=("Segoe UI", 9, "bold")).pack(fill=tk.X, pady=(0, 5))
    windows = app.terminal.get_window_list()
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
        cwd = app.terminal.get_process_cwd(hwnd)
        
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

        short_rid = rid.split("-")[-1] if rid and "-" in rid else (rid[:8] if rid else "?")
        worker_info = {
            "id": f"{hwnd}:{short_rid}",
            "status": "Connected",
            "role": role,
            "folder": selected_proj['local_path'] if selected_proj else "N/A",
            "kanban": selected_proj['kanban_project_name'] if selected_proj else "None",
            "start_time": time.time(),
            "terminal": title,
            "runtime_id": rid,
            "hwnd": hwnd,
            "pid": None # Manually connected
        }
        app.workers_mgr.add_worker(worker_info)
        
        app.refresh_worker_table()
        app.connect_to_hwnd(hwnd, title, rid)
        popup.destroy()

    ttk.Button(frame, text="Add to Monitoring", command=on_connect).pack(pady=10)

def open_add_project_popup(app):
    folder = filedialog.askdirectory(initialdir=os.getcwd(), title="Select Project Folder")
    if not folder: return
    popup = tk.Toplevel(app.root); popup.title("Project Details")
    utils_ui.center_popup(app.root, popup, 500, 300)
    frame = ttk.Frame(popup, padding="20"); frame.pack(fill=tk.BOTH, expand=True)
    ttk.Label(frame, text="ID (Unique):").pack(fill=tk.X)
    name_entry = ttk.Entry(frame); name_entry.insert(0, os.path.basename(folder)); name_entry.pack(fill=tk.X, pady=(0, 10))
    ttk.Label(frame, text="Kanban Project Name:").pack(fill=tk.X)
    kanban_entry = ttk.Entry(frame); kanban_entry.insert(0, name_entry.get()); kanban_entry.pack(fill=tk.X, pady=(0, 20))
    def on_save():
        new_id = name_entry.get().strip()
        if not new_id: return
        
        # Uniqueness check
        existing = engine_projects.load_projects()
        if any(p['name'] == new_id for p in existing):
            messagebox.showerror("Error", f"Project ID '{new_id}' already exists!")
            return

        if new_id and kanban_entry.get():
            engine_projects.add_project(new_id, folder, kanban_project_name=kanban_entry.get())
            app.refresh_project_table()
            popup.destroy()
    ttk.Button(frame, text="Save Project", command=on_save).pack()

def open_settings_popup(app):
    popup = tk.Toplevel(app.root); popup.title("Global Settings")
    utils_ui.center_popup(app.root, popup, 500, 750)
    main = ttk.Frame(popup, padding=20); main.pack(fill=tk.BOTH, expand=True)
    
    descriptions = {
        "ip": "The IP address of the Kanban server.",
        "port": "The network port for the Kanban API connection.",
        "last_project": "The project that will be selected by default on startup.",
        "last_user": "The default user to monitor in the Kanban board.",
        "poll_interval": "Seconds between Kanban API update checks.",
        "sync_interval_ms": "Milliseconds between terminal screen captures.",
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
        for key, val in app.full_config.get(section, {}).items():
            if isinstance(val, (str, int, float, bool)):
                f = ttk.Frame(main); f.pack(fill=tk.X, pady=2)
                label_text = key
                if key == "poll_interval": label_text = "poll_interval (s)"
                if key == "sync_interval_ms": label_text = "sync_interval (ms)"
                
                lbl = ttk.Label(f, text=f"{label_text}:", width=25)
                lbl.pack(side=tk.LEFT)
                if key in descriptions: utils_ui.ToolTip(lbl, descriptions[key])

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
                orig_val = app.full_config[sec][key]
                new_val_str = entry.get()
                if type(orig_val) is bool:
                    new_val = new_val_str.lower() in ("true", "1", "yes")
                elif isinstance(orig_val, int): new_val = int(new_val_str)
                elif isinstance(orig_val, float): new_val = float(new_val_str)
                else: new_val = new_val_str
                app.full_config[sec][key] = new_val
            utils_ui.save_full_config(app.full_config)
            popup.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Invalid value: {e}")
    
    ttk.Button(main, text="Save All", command=save).pack(pady=20)
