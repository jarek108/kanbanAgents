import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import time
import engine_projects
import utils_ui

def open_spawn_worker_popup(app):
    popup = tk.Toplevel(app.root)
    popup.title("Spawn Internal Worker")
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
        # Spawn via PTY manager
        app.workers_mgr.spawn_worker(selected_proj, role)
        popup.destroy()

    ttk.Button(frame, text="Spawn Worker", command=on_spawn).pack(pady=10)

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
    # Same as before, but maybe remove terminal scraping settings
    popup = tk.Toplevel(app.root); popup.title("Global Settings")
    utils_ui.center_popup(app.root, popup, 500, 600)
    main = ttk.Frame(popup, padding=20); main.pack(fill=tk.BOTH, expand=True)
    
    descriptions = {
        "ip": "The IP address of the Kanban server.",
        "port": "The network port for the Kanban API connection.",
        "poll_interval": "Seconds between Kanban API update checks.",
        "orch_geometry": "The Orchestrator's own window size and screen coordinates.",
        "show_terminal": "Determines if the Live Terminal Mirror is visible on startup."
    }

    sections = ["kanban", "ui"]
    entries = {}
    for section in sections:
        ttk.Label(main, text=f"[{section.upper()}]", font=("Segoe UI", 10, "bold")).pack(fill=tk.X, pady=(10, 5))
        for key, val in app.full_config.get(section, {}).items():
            if isinstance(val, (str, int, float, bool)):
                f = ttk.Frame(main); f.pack(fill=tk.X, pady=2)
                lbl = ttk.Label(f, text=f"{key}:", width=25)
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
    
    ttk.Button(main, text="Save Settings", command=save).pack(pady=20)
