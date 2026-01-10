import tkinter as tk
import os
import json
import threading
import time

# Global lock to prevent concurrent file access within the same process
_config_lock = threading.Lock()

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text: return
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT, background="#2d2d2d", foreground="#d4d4d4",
                      relief=tk.SOLID, borderwidth=1, font=("Segoe UI", "9", "normal"), padx=5, pady=3)
        label.pack()

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw: tw.destroy()

def get_config_path():
    cfg_path = os.path.join(os.path.dirname(__file__), "orchestrator_config.json")
    template_path = os.path.join(os.path.dirname(__file__), "orchestrator_config.template.json")
    if not os.path.exists(cfg_path) and os.path.exists(template_path):
        import shutil
        shutil.copy(template_path, cfg_path)
    return cfg_path

def load_full_config():
    cfg_path = get_config_path()
    with _config_lock:
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[utils_ui Load Error] {e}")
    return {}

def save_full_config(config):
    cfg_path = get_config_path()
    temp_path = cfg_path + ".tmp"
    
    with _config_lock:
        try:
            with open(temp_path, 'w') as f:
                json.dump(config, f, indent=4)
            
            # Retry loop for Windows file contention
            for i in range(5):
                try:
                    if os.path.exists(cfg_path):
                        os.replace(temp_path, cfg_path)
                    else:
                        os.rename(temp_path, cfg_path)
                    return True
                except PermissionError:
                    time.sleep(0.1)
            raise PermissionError(f"Could not replace {cfg_path} after 5 attempts")
            
        except Exception as e:
            print(f"[Config Save Error] {e}")
            if os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass
            return False

def center_popup(root, popup, width, height):
    root.update_idletasks()
    px = root.winfo_rootx() + (root.winfo_width() // 2) - (width // 2)
    py = root.winfo_rooty() + (root.winfo_height() // 2) - (height // 2)
    popup.geometry(f"{width}x{height}+{px}+{py}")
    popup.transient(root)
    popup.grab_set()