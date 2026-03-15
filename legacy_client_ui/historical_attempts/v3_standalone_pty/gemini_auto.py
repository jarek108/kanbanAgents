import engine_pty
import time
import sys
import re
import threading
import terminal_emulator
import html
import os
import msvcrt
import ctypes

def enable_ansi():
    if os.name == 'nt':
        kernel32 = ctypes.windll.kernel32
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        # ENABLE_PROCESSED_OUTPUT = 0x0001
        # 0x0001 | 0x0002 | 0x0004 = 7
        handle = kernel32.GetStdHandle(-11) # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)

def main():
    enable_ansi()
    
    # Setup terminal emulation
    cols, rows = 120, 30
    screen = terminal_emulator.TerminalScreen(cols=cols, rows=rows)
    screen_lock = threading.Lock()
    
    # Use the project's existing PTY engine
    pty = engine_pty.PTY(cols=cols, rows=rows)
    
    monitor_file = "terminal_monitor.html"
    
    def on_output(text):
        # Print output to console
        sys.stdout.write(text)
        sys.stdout.flush()
        
        # Feed to emulator for monitoring
        with screen_lock:
            screen.feed(text)
        
        # Auto-reply logic from gemini.exp
        if re.search(r"(?i)keep trying", text):
            # Log to stderr to avoid breaking the ANSI stream on stdout
            sys.stderr.write("\n*** Auto-Reply: Saw 'keep trying', sending 1... ***\n")
            sys.stderr.flush()
            # Send the option '1' and Enter
            pty.write("1\r\n")
            time.sleep(0.5)

    pty.on_output = on_output
    
    # Background thread to dump HTML state
    def monitor_loop():
        while pty.running:
            try:
                with screen_lock:
                    content = screen.get_text()
                
                escaped_content = html.escape(content)
                html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="3">
    <title>Gemini Auto Monitor</title>
    <style>
        body {{ background-color: #1e1e1e; color: #d4d4d4; font-family: 'Consolas', 'Courier New', monospace; padding: 20px; font-size: 14px; line-height: 1.2; }}
        pre {{ margin: 0; white-space: pre; }}
    </style>
</head>
<body>
    <pre>{escaped_content}</pre>
    <div style="margin-top: 20px; font-size: 10px; color: #666;">Last Update: {time.strftime('%H:%M:%S')}</div>
</body>
</html>"""
                
                # Atomic write
                tmp_file = monitor_file + ".tmp"
                with open(tmp_file, "w", encoding="utf-8") as f:
                    f.write(html_body)
                os.replace(tmp_file, monitor_file)
                
            except Exception as e:
                # Log to stderr
                sys.stderr.write(f"\n[Monitor Error] {e}\n")
            
            time.sleep(3)

    # We need to run via cmd.exe /c because gemini is a .cmd file on Windows
    command = "cmd.exe /c gemini -y"
    
    sys.stderr.write(f"--- Starting Automated Gemini Session (Windows Native) ---\n")
    sys.stderr.write(f"--- Monitoring active: Open {os.path.abspath(monitor_file)} in your browser ---\n")
    try:
        pty.spawn(command)
    except Exception as e:
        sys.stderr.write(f"Error spawning gemini: {e}\n")
        return

    # Start monitor thread
    mt = threading.Thread(target=monitor_loop, daemon=True)
    mt.start()

    # Thread to handle user input (mimics 'interact' in Expect)
    def input_thread():
        while pty.running:
            try:
                if msvcrt.kbhit():
                    char = msvcrt.getwch()
                    if char == '\r':
                        pty.write('\r\n')
                    elif char == '\x03': # Ctrl+C
                        pty.write('\x03')
                    elif char in ('\x00', '\xe0'):
                        # Special keys (arrows, etc) - read second part
                        char2 = msvcrt.getwch()
                        # Map Windows scan codes to ANSI escape sequences for the PTY
                        mapping = {
                            'H': '\x1b[A', # Up
                            'P': '\x1b[B', # Down
                            'M': '\x1b[C', # Right
                            'K': '\x1b[D', # Left
                            'G': '\x1b[H', # Home
                            'O': '\x1b[F', # End
                            'S': '\x1b[3~', # Delete
                        }
                        if char2 in mapping:
                            pty.write(mapping[char2])
                    else:
                        pty.write(char)
                else:
                    time.sleep(0.001) # Faster response
            except Exception:
                break

    it = threading.Thread(target=input_thread, daemon=True)
    it.start()

    # Keep the main thread alive while the process is running
    try:
        while pty.running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        sys.stderr.write("\nStopping...\n")
        pty.close()
    
    sys.stderr.write("\n--- Session Ended ---\n")

if __name__ == "__main__":
    main()
    try:
        while pty.running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping...")
        pty.close()
    
    print("\n--- Session Ended ---")

if __name__ == "__main__":
    main()
