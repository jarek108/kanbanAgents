import os
import sys
import subprocess
import signal
import time
from pathlib import Path

# Configuration
SCRIPT_NAME = "screenshot_listener.py"
TOOLS_DIR = Path(__file__).parent
LISTENER_PATH = TOOLS_DIR / SCRIPT_NAME

def get_pythonw():
    """Find the correct pythonw executable in the current environment."""
    python_exe = sys.executable
    # Check if we're in a Scripts folder (Windows venv)
    bin_dir = os.path.dirname(python_exe)
    pythonw_exe = os.path.join(bin_dir, "pythonw.exe")
    
    if os.path.exists(pythonw_exe):
        return pythonw_exe
    
    # Fallback to string replacement
    pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")
    if os.path.exists(pythonw_exe):
        return pythonw_exe
        
    return "pythonw"

def get_running_processes():
    """Find all python processes running our listener script."""
    processes = []
    try:
        # Get all python processes and their command lines
        cmd = 'Get-WmiObject Win32_Process | Where-Object { $_.Name -like "python*" } | Select-Object ProcessId, CommandLine | ConvertTo-Json'
        output = subprocess.check_output(["powershell", "-Command", cmd], text=True).strip()
        
        if not output:
            return []
            
        import json
        data = json.loads(output)
        
        # PowerShell might return a single dict or a list of dicts
        if isinstance(data, dict):
            data = [data]
            
        for proc in data:
            cmd_line = proc.get("CommandLine", "")
            if cmd_line and SCRIPT_NAME.lower() in cmd_line.lower():
                processes.append(int(proc.get("ProcessId")))
    except Exception as e:
        # Fallback to a simpler check if the above fails
        try:
            cmd = f'Get-Process | Where-Object {{ $_.CommandLine -like "*{SCRIPT_NAME}*" }} | Select-Object -ExpandProperty Id'
            output = subprocess.check_output(["powershell", "-Command", cmd], text=True)
            for line in output.splitlines():
                if line.strip().isdigit():
                    processes.append(int(line.strip()))
        except:
            pass
    return processes

def stop():
    """Stop all running instances of the listener."""
    pids = get_running_processes()
    if not pids:
        print("No listener processes found.")
        return True
    
    print(f"Stopping {len(pids)} listener process(es)...")
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"  - Killed process {pid}")
        except OSError:
            # Try a more forceful kill if needed
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
            print(f"  - Force killed process {pid}")
    
    # Verify they are gone
    time.sleep(1)
    if not get_running_processes():
        print("Successfully stopped all listeners.")
        return True
    return False

def start():
    """Start the listener in the background and report errors if it fails."""
    if get_running_processes():
        print("Listener is already running. Use 'restart' to refresh.")
        return False
    
    pw = get_pythonw()
    print(f"Starting listener: {pw} {LISTENER_PATH}")
    
    # Use Popen to launch and detached from the current console
    subprocess.Popen(
        [pw, str(LISTENER_PATH)],
        cwd=str(TOOLS_DIR),
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait a moment for it to initialize
    time.sleep(2)
    
    if get_running_processes():
        print("Listener started successfully (Background).")
        return True
    else:
        print("\nERROR: Listener failed to start.")
        print("Capturing diagnostic info...")
        try:
            # Run it synchronously for a brief moment with the standard python.exe 
            # to capture the error output.
            python_exe = sys.executable
            result = subprocess.run(
                [python_exe, str(LISTENER_PATH)],
                cwd=str(TOOLS_DIR),
                capture_output=True,
                text=True,
                timeout=3 # Give it 3 seconds to fail
            )
            if result.stderr:
                print("-" * 40)
                print("STARTUP ERROR LOG:")
                print(result.stderr.strip())
                print("-" * 40)
            else:
                print("No specific error captured in stderr. The process simply exited.")
        except subprocess.TimeoutExpired as e:
            if e.stderr:
                print("Captured during timeout:")
                print(e.stderr.decode().strip())
            else:
                print("The process did not exit immediately, but is not being detected as running.")
        except Exception as e:
            print(f"Diagnostics failed: {e}")
        return False

def status():
    """Show the status of the listener."""
    pids = get_running_processes()
    if pids:
        print(f"Status: RUNNING (PIDs: {', '.join(map(str, pids))})")
    else:
        print("Status: NOT RUNNING")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python manage_listener.py [start|stop|restart|status]")
        sys.exit(1)
    
    action = sys.argv[1].lower()
    
    if action == "start":
        start()
    elif action == "stop":
        stop()
    elif action == "restart":
        stop()
        start()
    elif action == "status":
        status()
    else:
        print(f"Unknown action: {action}")
        print("Available actions: start, stop, restart, status")
