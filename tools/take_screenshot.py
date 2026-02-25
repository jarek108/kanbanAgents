import os
import json
import win32clipboard
from datetime import datetime
from PIL import ImageGrab
from pathlib import Path

try:
    from notification_ui import show_notification
except ImportError:
    # Handle cases where it's run from a different context
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from notification_ui import show_notification

def set_clipboard_text(text):
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
    win32clipboard.CloseClipboard()

def capture_screenshot():
    # Load config
    config_path = Path(__file__).parent.parent / "screenshot_config.json"
    save_dir = Path(__file__).parent.parent / "artifacts"
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                custom_path = config.get("screenshot_path")
                if custom_path:
                    save_dir = Path(custom_path)
                    if not save_dir.is_absolute():
                        save_dir = Path(__file__).parent.parent / save_dir
        except Exception as e:
            print(f"Error loading config: {e}")

    # Ensure directory exists
    save_dir.mkdir(exist_ok=True, parents=True)
    
    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.jpg"
    filepath = save_dir / filename
    
    # Capture screen
    try:
        screenshot = ImageGrab.grab()
        screenshot.convert("RGB").save(filepath, "JPEG", quality=85)
        
        path_str = str(filepath.absolute())
        set_clipboard_text(path_str)
        
        print(f"Screenshot saved and path copied to clipboard: {path_str}")
        show_notification(f"Saved: {filename}")
        return path_str
    except Exception as e:
        print(f"Error taking screenshot: {e}")
        return None

if __name__ == "__main__":
    capture_screenshot()
