import os
import sys
import json
from pathlib import Path
from pynput import keyboard
from take_screenshot import capture_screenshot

# Add the current directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

def load_config():
    config_path = Path(__file__).parent.parent / "screenshot_config.json"
    default_hotkey = '<ctrl>+<alt>+s'
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                # Convert "Ctrl+Shift+P" style to "<ctrl>+<shift>+p" for pynput
                raw_hotkey = config.get("screenshot_hotkey", default_hotkey)
                # Clean up and format for pynput
                parts = raw_hotkey.lower().split("+")
                formatted_parts = []
                for p in parts:
                    p = p.strip()
                    if p in ["ctrl", "shift", "alt"]:
                        formatted_parts.append(f"<{p}>")
                    else:
                        formatted_parts.append(p)
                return "+".join(formatted_parts)
        except Exception as e:
            print(f"Error loading config: {e}")
    return default_hotkey

def on_activate():
    print("Hotkey triggered: Capturing screenshot...")
    capture_screenshot()

def start_listener():
    hotkey = load_config()
    print(f"Starting screenshot listener... Press {hotkey} to capture.")
    try:
        with keyboard.GlobalHotKeys({
            hotkey: on_activate
        }) as h:
            h.join()
    except Exception as e:
        print(f"Failed to start listener with hotkey {hotkey}: {e}")
        # Fallback to default if config fails
        with keyboard.GlobalHotKeys({'<ctrl>+<alt>+s': on_activate}) as h:
            h.join()

if __name__ == "__main__":
    start_listener()
