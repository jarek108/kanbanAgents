import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import os
from orchestrator_core import OrchestratorCore

class OrchestratorUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Project Orchestrator")
        
        self.core = OrchestratorCore()
        self.root.geometry(self.core.config.get("orch_geometry", "1100x700"))
        self.root.configure(bg="#1e1e1e")
        
        self.is_syncing = False
        self.active_project = None
        
        self.setup_styles()
        self.setup_ui()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Load initial project if exists
        if self.core.projects:
            self.project_var.set(self.core.projects[0]['name'])
            self.on_project_select()

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

        # --- PROJECT SELECTION BAR ---
        proj_bar = ttk.Frame(self.main_container, style="Header.TFrame", padding="10")
        proj_bar.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(proj_bar, text="Project:", style="Header.TLabel").pack(side=tk.LEFT, padx=(0, 5))
        self.project_var = tk.StringVar()
        self.project_dropdown = ttk.Combobox(proj_bar, textvariable=self.project_var, state="readonly", width=30)
        self.project_dropdown['values'] = [p['name'] for p in self.core.projects]
        self.project_dropdown.pack(side=tk.LEFT, padx=5)
        self.project_dropdown.bind("<<ComboboxSelected>>", self.on_project_select)

        ttk.Button(proj_bar, text="+ Add Project", command=self.open_add_project_popup).pack(side=tk.LEFT, padx=15)
        ttk.Button(proj_bar, text="Edit Projects", command=self.open_edit_projects_popup).pack(side=tk.LEFT)

        # --- INFO PANEL (Git & Kanban) ---
        info_frame = ttk.Frame(self.main_container, padding="5")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        self.git_label = ttk.Label(info_frame, text="Git: --", style="Info.TLabel")
        self.git_label.pack(side=tk.LEFT, padx=(0, 20))

        self.kanban_label = ttk.Label(info_frame, text="Kanban: --", style="Info.TLabel")
        self.kanban_label.pack(side=tk.LEFT)

        # --- WORKER LAUNCH BAR ---
        worker_bar = ttk.LabelFrame(self.main_container, text=" Orchestration ", padding="10")
        worker_bar.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(worker_bar, text="Role:").pack(side=tk.LEFT, padx=(0, 5))
        self.role_var = tk.StringVar()
        self.role_dropdown = ttk.Combobox(worker_bar, textvariable=self.role_var, state="readonly", width=15)
        self.role_dropdown['values'] = self.core.get_roles()
        if self.role_dropdown['values']: self.role_dropdown.current(0)
        self.role_dropdown.pack(side=tk.LEFT, padx=5)

        ttk.Button(worker_bar, text="Start Worker", command=self.start_worker).pack(side=tk.LEFT, padx=15)

        # --- MIRROR CONTROL BAR ---
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

    def on_project_select(self, event=None):
        name = self.project_var.get()
        self.active_project = next((p for p in self.core.projects if p['name'] == name), None)
        if self.active_project:
            branch, status = self.core.get_git_info(self.active_project['local_path'])
            self.git_label.config(text=f"Git: [{branch}] {status}")
            # Kanban info placeholder (could fetch from API)
            self.kanban_label.config(text=f"Kanban: {self.active_project['kanban_project_name']}")

    def open_add_project_popup(self):
        # 1. Immediate Folder Browser
        start_dir = os.getcwd()
        folder = filedialog.askdirectory(initialdir=start_dir, title="Select Project Folder")
        if not folder: return

        # 2. Details Popup
        popup = tk.Toplevel(self.root)
        popup.title("Project Details")
        popup.geometry("500x300")
        popup.configure(bg="#1e1e1e")
        
        # Center on parent
        self.root.update_idletasks()
        px = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - 250
        py = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - 150
        popup.geometry(f"+{px}+{py}")
        
        popup.transient(self.root)
        popup.grab_set()

        frame = ttk.Frame(popup, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Name (Alias):").pack(fill=tk.X)
        name_entry = ttk.Entry(frame)
        name_entry.insert(0, os.path.basename(folder))
        name_entry.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame, text="Local Path:").pack(fill=tk.X)
        path_label = ttk.Label(frame, text=folder, style="Info.TLabel")
        path_label.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame, text="Kanban Project Name:").pack(fill=tk.X)
        kanban_entry = ttk.Entry(frame)
        kanban_entry.insert(0, name_entry.get()) # Suggest same as name
        kanban_entry.pack(fill=tk.X, pady=(0, 20))

        def on_save():
            n, k = name_entry.get(), kanban_entry.get()
            if n and k:
                self.core.add_project(n, folder, k)
                self.project_dropdown['values'] = [prj['name'] for prj in self.core.projects]
                self.project_var.set(n)
                self.on_project_select()
                popup.destroy()
            else:
                messagebox.showerror("Error", "Name and Kanban Name required.")

        ttk.Button(frame, text="Save Project", command=on_save).pack()

    def open_edit_projects_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Manage Projects")
        popup.geometry("600x400")
        popup.configure(bg="#1e1e1e")
        
        # Center
        self.root.update_idletasks()
        px = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - 300
        py = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - 200
        popup.geometry(f"+{px}+{py}")
        
        popup.transient(self.root)
        popup.grab_set()

        main_frame = ttk.Frame(popup, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas/Scrollbar for long lists
        canvas = tk.Canvas(main_frame, bg="#1e1e1e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def refresh_list():
            for widget in scroll_frame.winfo_children():
                widget.destroy()
            
            for p in self.core.projects:
                p_frame = ttk.LabelFrame(scroll_frame, text=f" {p['name']} ", padding="10")
                p_frame.pack(fill=tk.X, pady=5, padx=5)
                
                ttk.Label(p_frame, text=f"Path: {p['local_path']}", font=("Segoe UI", 8)).pack(anchor="w")
                ttk.Label(p_frame, text=f"Kanban: {p['kanban_project_name']}", font=("Segoe UI", 8)).pack(anchor="w")
                
                btn_frame = ttk.Frame(p_frame)
                btn_frame.pack(fill=tk.X, pady=(5, 0))
                
                def delete_p(name=p['name']):
                    if messagebox.askyesno("Delete", f"Remove '{name}' from projects?"):
                        self.core.delete_project(name)
                        self.project_dropdown['values'] = [prj['name'] for prj in self.core.projects]
                        if self.project_var.get() == name:
                            self.project_var.set(self.project_dropdown['values'][0] if self.core.projects else "")
                            self.on_project_select()
                        refresh_list()

                ttk.Button(btn_frame, text="Remove", command=delete_p).pack(side=tk.RIGHT)

        refresh_list()

    def start_worker(self):
        if not self.active_project:
            messagebox.showwarning("Warning", "Please select a project first.")
            return
        role = self.role_var.get()
        if not role:
            messagebox.showwarning("Warning", "Please select a role.")
            return
        
        # Launch window
        title = self.core.launch_worker(self.active_project, role)
        
        # Auto-connect mirror after a short delay to let window spawn
        self.root.after(1500, lambda: self.connect_by_title(title))

    def connect_by_title(self, title):
        windows = self.core.get_window_list()
        for t, h in windows:
            if title.lower() in t.lower():
                self.connect_to_hwnd(h, t)
                return
        print(f"Could not auto-connect to: {title}")

    def connect_to_hwnd(self, hwnd, title):
        if self.core.connect_to_hwnd(hwnd, title):
            self.status_icon.config(fg="green")
            self.status_label.config(text=f"Mirroring: {title[:20]}...")
            if not self.is_syncing:
                self.is_syncing = True
                self.periodic_sync()

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

    def on_closing(self):
        self.core.save_config({"orch_geometry": self.root.geometry()})
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = OrchestratorUI(root)
    root.mainloop()
