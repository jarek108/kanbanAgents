import sys
import os
import ctypes
from pathlib import Path
from datetime import datetime

# Font loading fix for Windows
def load_font(font_path):
    if os.name == 'nt':
        FR_PRIVATE = 0x10
        ctypes.windll.gdi32.AddFontResourceExW(str(font_path), FR_PRIVATE, 0)

# Add tools folder to path
tools_path = str(Path(__file__).parent / "tools")
if tools_path not in sys.path:
    sys.path.append(tools_path)

# Change directory to script location to help with asset loading
os.chdir(Path(__file__).parent)

# Try to load CTK font manually before importing ctk
venv_base = Path("C:/Users/chojn/jarvis/jarvis-venv")
ctk_font_path = venv_base / "Lib/site-packages/customtkinter/assets/fonts/CustomTkinter_shapes_font.otf"
if ctk_font_path.exists():
    load_font(ctk_font_path)

import customtkinter as ctk
from launch_gemini_session import get_sessions, launch_session
from take_screenshot import capture_screenshot
import threading
import win32con
import json

class HotkeyManager(threading.Thread):
    def __init__(self, hotkey_str, callback):
        super().__init__(daemon=True)
        self.hotkey_str = hotkey_str
        self.callback = callback
        
        self.key_map = {
            "F1": win32con.VK_F1, "F2": win32con.VK_F2, "F3": win32con.VK_F3,
            "F4": win32con.VK_F4, "F5": win32con.VK_F5, "F6": win32con.VK_F6,
            "F7": win32con.VK_F7, "F8": win32con.VK_F8, "F9": win32con.VK_F9,
            "F10": win32con.VK_F10, "F11": win32con.VK_F11, "F12": win32con.VK_F12,
            "P": 0x50 # VK_P
        }
        self.mod_map = {
            "CTRL": win32con.MOD_CONTROL,
            "SHIFT": win32con.MOD_SHIFT,
            "ALT": win32con.MOD_ALT
        }

    def parse_hotkey(self):
        parts = self.hotkey_str.upper().split('+')
        mods = 0
        vk = 0
        for p in parts:
            p = p.strip()
            if p in self.mod_map:
                mods |= self.mod_map[p]
            elif p in self.key_map:
                vk = self.key_map[p]
            elif len(p) == 1:
                vk = ord(p)
        return mods, vk

    def run(self):
        mods, vk = self.parse_hotkey()
        if not vk:
            print(f"Invalid hotkey: {self.hotkey_str}")
            return
            
        user32 = ctypes.windll.user32
        if user32.RegisterHotKey(None, 1, mods, vk):
            try:
                msg = ctypes.wintypes.MSG()
                while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                    if msg.message == win32con.WM_HOTKEY:
                        self.callback()
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
            finally:
                user32.UnregisterHotKey(None, 1)
        else:
            print(f"Failed to register hotkey {self.hotkey_str}")

class GeminiLauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Load Config
        self.load_config()
        
        # Start Global Hotkey Listener
        self.hotkey_thread = HotkeyManager(self.config.get("screenshot_hotkey", "F9"), self.take_screenshot_action)
        self.hotkey_thread.start()

        self.title("Gemini CLI Launcher")
        self.geometry("1100x700")
        self.configure(fg_color="#121212") # Set dark background for root
        
        # State
        self.sessions = []
        self.sort_col = "mtime"
        self.sort_reverse = True
        self.selected_session = {"uuid": "latest", "index": "L", "summary": "Latest Active Session"}
        
        # Layout
        self.grid_columnconfigure(0, weight=1) # Session Table Area
        self.grid_columnconfigure(1, weight=1) # Action Panel
        self.grid_rowconfigure(0, weight=1)
        
        # --- Left Side: Session Table ---
        self.left_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#1a1a1a")
        self.left_frame.grid(row=0, column=0, sticky="nsew")
        self.left_frame.grid_rowconfigure(2, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)
        
        self.sidebar_label = ctk.CTkLabel(self.left_frame, text="Sessions", 
                                          font=ctk.CTkFont(size=20, weight="bold"))
        self.sidebar_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Table Header
        self.header_frame = ctk.CTkFrame(self.left_frame, fg_color="#252525", height=35, corner_radius=0)
        self.header_frame.grid(row=1, column=0, sticky="ew", padx=10)
        self.header_frame.grid_columnconfigure(0, weight=3) # Summary
        self.header_frame.grid_columnconfigure(1, weight=1) # Updated
        
        self.btn_sort_sum = ctk.CTkButton(self.header_frame, text="Summary", fg_color="transparent", 
                                          text_color="white", anchor="w", font=ctk.CTkFont(weight="bold"),
                                          command=lambda: self.set_sort("summary"))
        self.btn_sort_sum.grid(row=0, column=0, sticky="ew", padx=(10, 0))
        
        self.btn_sort_time = ctk.CTkButton(self.header_frame, text="Updated", fg_color="transparent", 
                                           text_color="white", anchor="e", font=ctk.CTkFont(weight="bold"),
                                           command=lambda: self.set_sort("mtime"))
        self.btn_sort_time.grid(row=0, column=1, sticky="ew", padx=(0, 20))

        # Scrollable Table Body
        self.table_container = ctk.CTkScrollableFrame(self.left_frame, fg_color="transparent", corner_radius=0)
        self.table_container.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.table_container.columnconfigure(0, weight=1)
        
        self.new_session_btn = ctk.CTkButton(self.left_frame, text="+ New Session", 
                                             command=self.select_new_session,
                                             fg_color="#2d2d2d", hover_color="#3d3d3d")
        self.new_session_btn.grid(row=3, column=0, padx=20, pady=20, sticky="ew")
        
        # --- Right Side: Main Panel ---
        self.main_panel = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_panel.grid(row=0, column=1, sticky="nsew", padx=30, pady=20)
        self.main_panel.grid_columnconfigure(0, weight=1)
        self.main_panel.grid_rowconfigure(2, weight=1)
        
        # Header with Screenshot Button
        self.header_frame_right = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        self.header_frame_right.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.header_frame_right.grid_columnconfigure(0, weight=1)
        
        self.header_label = ctk.CTkLabel(self.header_frame_right, text="Latest Active Session", 
                                         font=ctk.CTkFont(size=18, weight="bold"), anchor="w")
        self.header_label.grid(row=0, column=0, sticky="nw")

        self.screenshot_btn = ctk.CTkButton(self.header_frame_right, text="📸 Screenshot", 
                                            width=120, height=32,
                                            fg_color="#333333", hover_color="#444444",
                                            command=self.take_screenshot_action)
        self.screenshot_btn.grid(row=0, column=1, sticky="ne")
        
        # Prompt Area
        self.prompt_label = ctk.CTkLabel(self.main_panel, text="Operation String:", font=ctk.CTkFont(size=14))
        self.prompt_label.grid(row=1, column=0, sticky="nw")
        
        self.prompt_textbox = ctk.CTkTextbox(self.main_panel, font=ctk.CTkFont(size=14),
                                             fg_color="#1d1e1e", text_color="#DCE4EE",
                                             border_width=1, border_color="#333333")
        self.prompt_textbox.grid(row=2, column=0, sticky="nsew", pady=(5, 20))
        
        # Configuration Row
        self.config_frame = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        self.config_frame.grid(row=3, column=0, sticky="ew")
        self.config_frame.grid_columnconfigure((0,1,2), weight=1)
        
        # Model Dropdown
        self.model_label = ctk.CTkLabel(self.config_frame, text="Model:", font=ctk.CTkFont(size=12))
        self.model_label.grid(row=0, column=0, sticky="w")
        self.model_menu = ctk.CTkOptionMenu(self.config_frame, 
                                            values=["gemini-3-flash-preview", "gemini-2.0-flash-exp", "gemini-2.0-pro-exp-02-05"])
        self.model_menu.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        
        # Preserve Toggle
        self.preserve_switch = ctk.CTkSwitch(self.config_frame, text="Preserve Session")
        self.preserve_switch.select()
        self.preserve_switch.grid(row=1, column=1)
        
        # Auto-Close Toggle
        self.close_switch = ctk.CTkSwitch(self.config_frame, text="Auto-Close")
        self.close_switch.grid(row=1, column=2)
        
        # Action Buttons
        self.button_frame = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        self.button_frame.grid(row=4, column=0, sticky="ew", pady=(30, 0))
        self.button_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.execute_btn = ctk.CTkButton(self.button_frame, text="Execute String", 
                                         command=self.execute_string,
                                         height=40, font=ctk.CTkFont(weight="bold"))
        self.execute_btn.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        
        self.open_btn = ctk.CTkButton(self.button_frame, text="Open Interactive", 
                                      command=self.open_interactive,
                                      height=40, fg_color="#444444", hover_color="#555555")
        self.open_btn.grid(row=0, column=1, padx=(10, 0), sticky="ew")
        
        # Initial Load
        self.refresh_sessions()

    def load_config(self):
        self.config = {"screenshot_path": "artifacts", "screenshot_hotkey": "F9"}
        config_path = Path(__file__).parent / "launcher_config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    self.config.update(json.load(f))
            except Exception as e:
                print(f"Error loading launcher_config.json: {e}")

    def refresh_sessions(self):
        self.sessions = get_sessions()
        self.render_table()

    def set_sort(self, col):
        if self.sort_col == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_col = col
            self.sort_reverse = True if col == "mtime" else False
        self.render_table()

    def render_table(self):
        sorted_sessions = sorted(self.sessions, key=lambda x: x[self.sort_col], reverse=self.sort_reverse)
        for widget in self.table_container.winfo_children():
            widget.destroy()
            
        for i, s in enumerate(sorted_sessions):
            row = ctk.CTkFrame(self.table_container, fg_color="transparent", corner_radius=0, cursor="hand2")
            row.pack(fill="x")
            row.grid_columnconfigure(0, weight=3)
            row.grid_columnconfigure(1, weight=1)
            
            is_selected = s['uuid'] == self.selected_session['uuid']
            if is_selected:
                row.configure(fg_color="#2d2d2d")
            else:
                if i % 2 == 0:
                    row.configure(fg_color="#212121")
            
            time_str = ""
            if s['mtime'] > 0:
                dt = datetime.fromtimestamp(s['mtime'])
                time_str = dt.strftime("%m/%d %H:%M")
            
            summary = s['summary']
            if len(summary) > 70: summary = summary[:67] + "..."
            
            # Using specific colors for better visibility in dark theme
            l2 = ctk.CTkLabel(row, text=summary, font=ctk.CTkFont(size=12), 
                              anchor="w", text_color="#DCE4EE") 
            l2.grid(row=0, column=0, padx=(15, 5), pady=8, sticky="ew")
            
            l3 = ctk.CTkLabel(row, text=time_str, font=ctk.CTkFont(size=11), 
                              text_color="#888888", anchor="e") 
            l3.grid(row=0, column=1, padx=(5, 20), pady=8, sticky="e")
            
            for w in [row, l2, l3]:
                w.bind("<Button-1>", lambda e, data=s: self.select_session(data))

    def select_session(self, session_data):
        self.selected_session = session_data
        self.header_label.configure(text=f"Session: {session_data['summary'][:40]}...")
        self.render_table()

    def select_new_session(self):
        self.selected_session = {"uuid": "new", "index": "N", "summary": "Brand New Session"}
        self.header_label.configure(text="New Session")
        self.render_table()

    def take_screenshot_action(self):
        path = capture_screenshot()
        if path:
            orig_text = self.screenshot_btn.cget("text")
            self.screenshot_btn.configure(text="✅ Saved!")
            self.after(1000, lambda: self.screenshot_btn.configure(text=orig_text))

    def execute_string(self):
        op = self.prompt_textbox.get("1.0", "end-1c")
        if not op.strip():
            self.prompt_textbox.configure(border_color="red")
            self.after(1000, lambda: self.prompt_textbox.configure(border_color="#333333"))
            return
            
        success = launch_session(
            operation=op,
            session_id=self.selected_session['uuid'],
            model=self.model_menu.get(),
            preserve=self.preserve_switch.get() == 1,
            close=self.close_switch.get() == 1
        )
        if success:
            self.after(2000, self.refresh_sessions)

    def open_interactive(self):
        launch_session(
            operation=" ",
            session_id=self.selected_session['uuid'],
            model=self.model_menu.get(),
            preserve=self.preserve_switch.get() == 1,
            close=False
        )
        self.after(2000, self.refresh_sessions)

if __name__ == "__main__":
    app = GeminiLauncherApp()
    app.mainloop()
