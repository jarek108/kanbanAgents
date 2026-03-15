import sys
import os
import time
import re
import threading

# Add 'tools' directory to the path so we can import project modules
sys.path.append(os.path.join(os.path.dirname(__file__), "tools"))

import engine_pty
import terminal_emulator

def main():
    # Setup terminal emulation
    cols, rows = 120, 30
    screen = terminal_emulator.TerminalScreen(cols=cols, rows=rows)
    screen_lock = threading.Lock()
    
    # Use the project's existing PTY engine
    pty = engine_pty.PTY(cols=cols, rows=rows)
    
    log_dir = "gemini_session_log"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    raw_log_path = os.path.join(log_dir, "raw_session.log")
    # Start with fresh log
    with open(raw_log_path, "w") as f:
        f.write("")

    def on_output(text):
        # 1. Feed to emulator
        with screen_lock:
            screen.feed(text)
        
        # 2. Append to raw log
        with open(raw_log_path, "a", encoding="utf-8", errors="ignore") as f:
            f.write(text)
        
        # 3. Auto-reply logic from gemini.exp
        if re.search(r"(?i)keep trying", text):
            # Send '1' and Enter (using \r as it's common for PTY)
            pty.write("1\r")

    pty.on_output = on_output
    
    # Background thread to dump clean state to console
    def dump_loop():
        while pty.running:
            try:
                with screen_lock:
                    content = screen.get_text()
                
                # ANSI Clear Screen and Home
                sys.stdout.write("\033[H\033[2J")
                sys.stdout.write(content)
                sys.stdout.write(f"\n\n--- Last Sync: {time.strftime('%H:%M:%S')} ---\n")
                sys.stdout.write("--- Press Ctrl+C to terminate session ---\n")
                sys.stdout.flush()
                
            except Exception as e:
                pass
            
            time.sleep(1.5)

    # We need to run via cmd.exe /c because gemini is a .cmd file on Windows
    command = "cmd.exe /c gemini -y"
    
    try:
        pty.spawn(command)
    except Exception as e:
        print(f"Error spawning gemini: {e}")
        return

    # Start dump thread
    dt = threading.Thread(target=dump_loop, daemon=True)
    dt.start()

    # Keep main thread alive
    try:
        while pty.running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pty.close()
    
    print("\n--- Session Ended ---")

if __name__ == "__main__":
    main()
