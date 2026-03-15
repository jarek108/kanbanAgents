import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import engine_terminal

class TerminalMirrorStandalone:
    def __init__(self, root):
        self.root = root
        self.root.title("Terminal Mirror Standalone")
        self.engine = engine_terminal.TerminalEngine()
        self.config = engine_terminal.load_config()
        self.root.geometry(self.config.get("last_geometry", "800x600"))
        
        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Auto connect
        last = self.config.get("last_title")
        if last: self.auto_connect(last)

    def setup_ui(self):
        self.root.configure(bg="#1e1e1e")
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        
        header = ttk.Frame(main)
        header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(header, text="Select Window", command=self.select_window).pack(side=tk.LEFT)
        self.status = ttk.Label(header, text="Disconnected", foreground="red")
        self.status.pack(side=tk.LEFT, padx=10)
        
        self.text = scrolledtext.ScrolledText(main, bg="black", fg="#d4d4d4", font=("Consolas", 10))
        self.text.pack(fill=tk.BOTH, expand=True)
        
        self.cmd = ttk.Entry(main)
        self.cmd.pack(fill=tk.X, pady=(10, 0))
        self.cmd.bind("<Return>", self.send)

    def select_window(self):
        # Quick popup
        pop = tk.Toplevel(self.root); pop.title("Select"); pop.geometry("300x400")
        lb = tk.Listbox(pop)
        lb.pack(fill=tk.BOTH, expand=True)
        wins = self.engine.get_window_list()
        for t, h in wins: lb.insert(tk.END, t)
        def go():
            if lb.curselection():
                t = lb.get(lb.curselection()[0])
                h = next(wh for wt, wh in wins if wt == t)
                self.connect(h, t); pop.destroy()
        ttk.Button(pop, text="Connect", command=go).pack()

    def connect(self, hwnd, title):
        if self.engine.connect(hwnd, title):
            self.status.config(text=f"Connected: {title[:20]}", foreground="green")
            threading.Thread(target=self.sync_loop, daemon=True).start()

    def auto_connect(self, title):
        for t, h in self.engine.get_window_list():
            if title.lower() in t.lower(): self.connect(h, t); return

    def sync_loop(self):
        while self.engine.connected_hwnd:
            content = self.engine.get_buffer_text()
            if content: self.root.after(0, self.update_ui, content)
            import time
            time.sleep(self.config.get("sync_interval_ms", 1000) / 1000.0)

    def update_ui(self, content):
        self.text.config(state='normal'); self.text.delete('1.0', tk.END)
        self.text.insert(tk.END, content); self.text.see(tk.END); self.text.config(state='disabled')

    def send(self, e):
        c = self.cmd.get()
        if c and self.engine.send_command(c): self.cmd.delete(0, tk.END)

    def on_closing(self):
        engine_terminal.save_config({"last_geometry": self.root.geometry()})
        self.root.destroy()

if __name__ == "__main__":
    r = tk.Tk(); app = TerminalMirrorStandalone(r); r.mainloop()
