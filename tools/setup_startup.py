import os
import sys
import winshell
from win32com.client import Dispatch

def setup_startup():
    # Paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    manage_script = os.path.join(current_dir, "manage_listener.py")
    
    # We use python.exe (not w) for the shortcut so it can run the management logic,
    # but the management logic itself will launch the background pythonw.
    python_exe = sys.executable

    startup_path = winshell.startup()
    shortcut_path = os.path.join(startup_path, "KanbanScreenshotListener.lnk")
    
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = python_exe
    shortcut.Arguments = f'"{manage_script}" start'
    shortcut.WorkingDirectory = current_dir
    shortcut.IconLocation = python_exe
    shortcut.Description = "Starts the background Kanban Screenshot listener"
    shortcut.WindowStyle = 7 # Minimized
    shortcut.save()
    
    print(f"Startup shortcut created at: {shortcut_path}")
    print(f"It will run: {python_exe} {manage_script} start")

if __name__ == "__main__":
    try:
        import winshell
    except ImportError:
        print("Installing winshell...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "winshell"])
        import winshell
        
    setup_startup()
