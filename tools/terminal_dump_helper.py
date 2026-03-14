import sys
import os

# Add current directory to path so we can import terminal_emulator
sys.path.append(os.path.dirname(__file__))
from terminal_emulator import TerminalScreen

def main():
    # Use argument or default
    log_path = sys.argv[1] if len(sys.argv) > 1 else "./gemini_session_log/raw_session.log"
    
    if not os.path.exists(log_path):
        return

    # Use a standard 120x30 grid
    screen = TerminalScreen(cols=120, rows=30)
    
    try:
        with open(log_path, "rb") as f:
            # We MUST process from the beginning because ANSI is stateful
            raw_data = f.read()
            data = raw_data.decode('utf-8', errors='ignore')
            screen.feed(data)
        
        # Print the grid state
        print(screen.get_text())
    except Exception as e:
        sys.stderr.write(f"Error rendering terminal: {e}\n")

if __name__ == "__main__":
    main()
