import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import os
import json
import webbrowser
import time
import manager_workers_pty
import manager_projects
import utils_ui
import orchestrator_popups_pty

class OrchestratorPTY:
    def __init__(self, root):
        self.root = root
        self.root.title("Project Orchestrator (Fully Interactive Terminal)")
        
        # Load main config for UI state
        self.full_config = utils_ui.load_full_config()
        
        geom = self.full_config.get("ui", {}).get("orch_geometry", "1200x850+50+50")
        self.root.geometry(geom)
        self.root.configure(bg="#1e1e1e")
        
        # --- MANAGERS ---
        self.projects_mgr = manager_projects.ProjectManager(self.full_config)
        self.workers_mgr = manager_workers_pty.WorkerManagerPTY(self.full_config)
        
        self.active_worker_id = None
        
        # Bind callbacks
        self.projects_mgr.on_update_callback = lambda: self.root.after(0, self.refresh_project_table)
        self.workers_mgr.on_update_callback = lambda: self.root.after(0, self.refresh_worker_table)
        self.workers_mgr.on_buffer_callback = self.on_buffer_update
        
        self.projects_mgr.start()
        
        self.setup_styles()
        self.setup_ui()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.refresh_project_table()
        self.periodic_refresh()

    def on_buffer_update(self, worker_id, full_text):
        if worker_id == self.active_worker_id:
            self.root.after(0, self.update_display, full_text)
        self.root.after(0, self.update_tree_stats, worker_id)

    def update_tree_stats(self, worker_id):
        for item in self.worker_tree.get_children():
            values = self.worker_tree.item(item, "values")
            if values and values[0] == worker_id:
                workers, _ = self.workers_mgr.get_workers()
                w = next((x for x in workers if x["id"] == worker_id), None)
                if w:
                    new_values = list(values)
                    new_values[5] = f"{w['size']:,}"
                    self.worker_tree.item(item, values=new_values)
                break

    def periodic_refresh(self):
        self.refresh_worker_table()
        self.root.after(1000, self.periodic_refresh)

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background="#1e1e1e")
        self.style.configure("TLabel", background="#1e1e1e", foreground="#d4d4d4", font=("Segoe UI", 9))
        self.style.configure("TButton", padding=(5, 1), font=("Segoe UI", 9))
        self.style.configure("Header.TFrame", background="#2d2d2d")
        self.style.configure("Header.TLabel", background="#2d2d2d", font=("Segoe UI", 9, "bold"))

    def setup_ui(self):
        self.main_container = ttk.Frame(self.root, padding="15")
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # --- PROJECT REGISTRY SECTION ---
        self.proj_sect = ttk.Frame(self.main_container)
        self.proj_sect.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(self.proj_sect, text="Project Registry", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        self.proj_content_frame = ttk.Frame(self.proj_sect, padding="5")
        self.proj_content_frame.pack(fill=tk.X)
        proj_btns = ttk.Frame(self.proj_content_frame)
        proj_btns.pack(side=tk.RIGHT, padx=5)
        ttk.Button(proj_btns, text="+ Add Project", command=lambda: orchestrator_popups_pty.open_add_project_popup(self)).pack(fill=tk.X, pady=2)
        p_cols = ("id", "path", "kanban", "status")
        self.project_tree = ttk.Treeview(self.proj_content_frame, columns=p_cols, show="headings", height=3)
        for c in p_cols: self.project_tree.heading(c, text=c.capitalize()); self.project_tree.column(c, width=150)
        self.project_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- WORKER TRACKING SECTION ---
        self.worker_sect = ttk.Frame(self.main_container)
        self.worker_sect.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(self.worker_sect, text="Internal Interactive Workers", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        self.worker_content = ttk.Frame(self.worker_sect, padding="5")
        self.worker_content.pack(fill=tk.X)
        worker_btns = ttk.Frame(self.worker_content)
        worker_btns.pack(side=tk.RIGHT, padx=5)
        ttk.Button(worker_btns, text="Spawn Worker", command=lambda: orchestrator_popups_pty.open_spawn_worker_popup(self)).pack(fill=tk.X, pady=2)
        ttk.Button(worker_btns, text="Kill Selected", command=self.kill_selected_worker).pack(fill=tk.X, pady=2)
        ttk.Button(worker_btns, text="Kill All", command=self.kill_all_workers).pack(fill=tk.X, pady=2)
        cols = ("id", "name", "status", "role", "project", "size", "time")
        self.worker_tree = ttk.Treeview(self.worker_content, columns=cols, show="headings", height=4)
        for c in cols: self.worker_tree.heading(c, text=c.capitalize()); self.worker_tree.column(c, width=120)
        self.worker_tree.column("id", width=100); self.worker_tree.column("name", width=130); self.worker_tree.column("project", width=130)
        self.worker_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.worker_tree.bind("<<TreeviewSelect>>", self.on_worker_select)

        # --- LIVE INTERACTIVE MIRROR ---
        self.mirror_sect = ttk.Frame(self.main_container)
        self.mirror_sect.pack(fill=tk.BOTH, expand=True)
        ttk.Label(self.mirror_sect, text="Interactive Terminal (Click to focus, type directly)", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        self.display_frame = ttk.Frame(self.mirror_sect, padding="5")
        self.display_frame.pack(fill=tk.BOTH, expand=True)
        self.terminal_display = tk.Text(
            self.display_frame, bg="#000000", fg="#d4d4d4", font=("Consolas", 10),
            padx=10, pady=10, borderwidth=0, undo=False, wrap=tk.NONE,
            insertofftime=0, cursor="xterm"
        )
        self.terminal_display.pack(fill=tk.BOTH, expand=True)
        
        # Cursor Tag
        self.terminal_display.tag_configure("cursor", background="#569cd6", foreground="black")

        # KEY BINDINGS FOR INTERACTIVITY - COMPREHENSIVE BLOCKING
        self.terminal_display.bind("<Key>", self.handle_keypress)
        self.terminal_display.bind("<Return>", lambda e: self.send_raw("\r"))
        self.terminal_display.bind("<BackSpace>", lambda e: self.send_raw("\b"))
        self.terminal_display.bind("<Delete>", lambda e: self.send_raw("\x1b[3~"))
        self.terminal_display.bind("<Tab>", lambda e: self.send_raw("\t"))
        self.terminal_display.bind("<Up>", lambda e: self.send_raw("\x1b[A"))
        self.terminal_display.bind("<Down>", lambda e: self.send_raw("\x1b[B"))
        self.terminal_display.bind("<Right>", lambda e: self.send_raw("\x1b[C"))
        self.terminal_display.bind("<Left>", lambda e: self.send_raw("\x1b[D"))
        self.terminal_display.bind("<Escape>", lambda e: self.send_raw("\x1b"))
        
        # Block common Tkinter shortcuts that interfere
        self.terminal_display.bind("<Control-BackSpace>", lambda e: self.send_raw("\x17")) # Ctrl+W (delete word)
        self.terminal_display.bind("<Control-a>", lambda e: "break")
        self.terminal_display.bind("<Control-v>", lambda e: "break")
        self.terminal_display.bind("<Control-c>", lambda e: self.send_raw("\x03"))

    def handle_keypress(self, event):
        # Allow scroll and focus but block text modification
        if event.char and ord(event.char) >= 32:
            self.send_raw(event.char)
        return "break"

    def send_raw(self, char_or_seq):
        if self.active_worker_id:
            self.workers_mgr.send_to_worker(self.active_worker_id, char_or_seq)
        return "break"

    def refresh_project_table(self):
        cache = self.projects_mgr.get_cache()
        for i in self.project_tree.get_children(): self.project_tree.delete(i)
        for name, info in cache.items():
            p = info['data']
            _, s, _, _, _ = info['git']
            self.project_tree.insert("", tk.END, values=(p['name'], p['local_path'], p['kanban_project_name'], s))

    def refresh_worker_table(self):
        workers, times = self.workers_mgr.get_workers()
        sel = self.worker_tree.selection()
        selected_id = self.worker_tree.item(sel[0])['values'][0] if sel else None
        for i in self.worker_tree.get_children(): self.worker_tree.delete(i)
        to_select = None
        for idx, w in enumerate(workers):
            iid = self.worker_tree.insert("", tk.END, values=(w['id'], w['terminal'], w['status'], w['role'], w['folder'], f"{w['size']:,}", times[idx]))
            if w['id'] == selected_id: to_select = iid
        if to_select: self.worker_tree.selection_set(to_select)

    def on_worker_select(self, event=None):
        sel = self.worker_tree.selection()
        if not sel: return
        w_id = self.worker_tree.item(sel[0])['values'][0]
        if w_id != self.active_worker_id:
            self.active_worker_id = w_id
            workers, _ = self.workers_mgr.get_workers()
            w = next((x for x in workers if x["id"] == w_id), None)
            if w: self.update_display(w['last_buffer'])

    def update_display(self, text):
        self.terminal_display.config(state='normal')
        self.terminal_display.delete('1.0', tk.END)
        self.terminal_display.insert(tk.END, text)
        
        # Render Cursor
        if self.active_worker_id:
            workers, _ = self.workers_mgr.get_workers()
            # We need to find the actual worker object to get the screen cursor
            # This is slightly inefficient but ensures consistency
            with self.workers_mgr.status_lock:
                target_w = next((w for w in self.workers_mgr.workers if w["id"] == self.active_worker_id), None)
                if target_w:
                    cx, cy = target_w["screen"].get_cursor()
                    # Convert to Tkinter index (1-based line, 0-based column)
                    idx = f"{cy+1}.{cx}"
                    self.terminal_display.tag_add("cursor", idx, f"{idx}+1c")
        
        self.terminal_display.see(tk.END)

    def kill_selected_worker(self):
        sel = self.worker_tree.selection()
        if not sel: return
        w_id = self.worker_tree.item(sel[0])['values'][0]
        if messagebox.askyesno("Kill Worker", f"Terminate worker {w_id}?"):
            self.workers_mgr.kill_worker(w_id)
            if self.active_worker_id == w_id:
                self.active_worker_id = None
                self.terminal_display.delete('1.0', tk.END)

    def kill_all_workers(self):
        if messagebox.askyesno("Kill All", "Terminate all internal workers?"):
            self.workers_mgr.stop_all(); self.active_worker_id = None
            self.terminal_display.delete('1.0', tk.END)

    def on_closing(self):
        self.projects_mgr.stop(); self.workers_mgr.stop_all()
        self.full_config["ui"]["orch_geometry"] = self.root.geometry()
        utils_ui.save_full_config(self.full_config); self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk(); app = OrchestratorPTY(root); root.mainloop()