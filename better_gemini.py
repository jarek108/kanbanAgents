import sys
import os
import time
import threading
import msvcrt
import re

# Ensure the 'tools' directory is accessible for imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

try:
    from tools.engine_pty import PTY
except ImportError:
    print("Error: Could not find 'tools/engine_pty.py'. Please run this script from the project root.")
    sys.exit(1)

def better_gemini():
    """
    Windows-native wrapper for Gemini CLI that automatically responds to 'keep trying' prompts.
    Uses ConPTY for 1:1 terminal behavior (colors, interactivity).
    """
    
    # Configuration: Matches typical terminal size
    pty = PTY(cols=120, rows=35)
    
    # Automation state
    last_reply_time = 0
    COOLDOWN_PERIOD = 2.0  # Seconds to wait before another auto-reply
    
    def on_output(text):
        nonlocal last_reply_time
        
        # 1. Immediate passthrough for 1:1 visual behavior (colors, cursor moves, etc.)
        sys.stdout.write(text)
        sys.stdout.flush()
        
        # 2. Monitor for the trigger phrase
        # We check the tail of the accumulated buffer in the PTY object
        full_buffer = pty.buffer
        
        # Search window handles cases where the trigger might be split across read chunks
        search_start = max(0, len(full_buffer) - 500)
        search_window = full_buffer[search_start:]
        
        if re.search(r"(?i)keep trying", search_window):
            now = time.time()
            # Cooldown prevents multiple triggers during UI redrawing
            if now - last_reply_time > COOLDOWN_PERIOD:
                last_reply_time = now
                
                # Subtle visual feedback that doesn't ruin the CLI layout
                sys.stdout.write("\033[93m*** [Auto-Reply] Saw 'keep trying', sending '1'... ***\033[0m")
                sys.stdout.flush()
                
                # Inject '1' and Enter into the process input
                pty.write("1")

    # Link the output handler
    pty.on_output = on_output

    print("\033[96m[Better Gemini] Starting native Windows wrapper with auto-retry...\033[0m")
    
    # Spawn the gemini process
    try:
        # Using 'cmd /c' ensures that .cmd and .ps1 files in the PATH are resolved correctly on Windows
        pty.spawn("cmd /c gemini -y")
    except Exception as e:
        print(f"\033[91mError spawning gemini: {e}\033[0m")
        return

    # 3. Input Loop (Keyboard -> PTY)
    # Forwards your input so you can interact normally
    def input_forwarder():
        while pty.running:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                
                # Exit wrapper on Ctrl+C
                if key == b'\x03':
                    pty.close()
                    break
                
                # Handle Special Keys (Arrows) to maintain 1:1 interactivity
                if key in (b'\x00', b'\xe0'):
                    next_key = msvcrt.getch()
                    # ANSI escape sequences for ConPTY input
                    mapping = {
                        b'H': '\033[A', # Up
                        b'P': '\033[B', # Down
                        b'M': '\033[C', # Right
                        b'K': '\033[D', # Left
                    }
                    if next_key in mapping:
                        pty.write(mapping[next_key])
                    continue
                
                # Forward regular characters
                try:
                    # msvcrt.getch returns bytes, PTY.write expects a string
                    pty.write(key.decode('utf-8', errors='ignore'))
                except Exception:
                    pass
            else:
                time.sleep(0.01)

    # Start the keyboard listener thread
    threading.Thread(target=input_forwarder, daemon=True).start()

    # 4. Wait for the process to exit
    try:
        while pty.running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pty.close()

    print("\033[96m[Better Gemini] Session finished.\033[0m")

if __name__ == "__main__":
    better_gemini()
