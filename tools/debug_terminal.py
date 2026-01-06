import win32gui
import win32con
import pyautogui
import pyperclip
import time
import sys
from PIL import ImageGrab

def debug_terminal_connection(target_title):
    print(f"Searching for window: '{target_title}'...")
    
    hwnd = None
    def enum_handler(h, ctx):
        nonlocal hwnd
        if win32gui.IsWindowVisible(h) and target_title.lower() in win32gui.GetWindowText(h).lower():
            hwnd = h
            
    win32gui.EnumWindows(enum_handler, None)
    
    if not hwnd:
        print(f"Error: Could not find window with title '{target_title}'")
        sys.exit(1)
        
    print(f"Found HWND: {hwnd}. Bringing to foreground...")
    
    try:
        # Bring to front and click to ensure focus
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        # Move to primary monitor to ensure screen coordinates are positive and visible
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 10, 10, 800, 600, win32con.SWP_SHOWWINDOW)
        time.sleep(0.5)
        win32gui.SetForegroundWindow(hwnd)
        
        # Click in the middle of the NEW window position
        rect = win32gui.GetWindowRect(hwnd)
        x = (rect[0] + rect[2]) // 2
        y = (rect[1] + rect[3]) // 2
        pyautogui.click(x, y)
        time.sleep(0.5) 

        print("Sending 'cls' then 'dir' command...")
        # Slow typing to ensure Windows Terminal registers it
        pyautogui.write("cls\n", interval=0.1)
        time.sleep(0.5)
        pyautogui.write("dir\n", interval=0.1)
        
        print("Waiting for command to complete...")
        time.sleep(2.0) 
        
        # Windows Terminal defaults:
        # Ctrl+Shift+A (Select All)
        # Ctrl+Shift+C (Copy)
        print("Capturing output via Windows Terminal shortcuts (Ctrl+Shift+A/C)...")
        pyperclip.copy("EMPTY_CLIPBOARD")
        
        pyautogui.hotkey('ctrl', 'shift', 'a')
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'shift', 'c')
        time.sleep(1.0)
        
        content = pyperclip.paste()

        # Screenshot for visual debug
        screenshot = ImageGrab.grab(bbox=rect)
        screenshot.save("screenshots/debug_terminal_view.jpg")
        print(f"Screenshot saved to screenshots/debug_terminal_view.jpg")
        
        print("-" * 40)
        print("CAPTURED CONTENT:")
        print("-" * 40)
        print(content)
        print("-" * 40)
        
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    target = "MyTerminal"
    debug_terminal_connection(target)