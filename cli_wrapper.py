import tkinter as tk
from tkinter import scrolledtext
import subprocess
import threading
import queue
import os
import sys

class GeminiCLIWrapper:
    """
    A simple GUI wrapper for the Gemini CLI.
    Approach 1: Using subprocess.Popen with PIPE for stdin/stdout and a background thread.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Gemini CLI Wrapper")
        
        # Position on Screen 1 (based on captured geometry: left=0, top=-1200)
        # and start maximized
        self.root.geometry("+0-1200")
        try:
            self.root.state('zoomed') # Windows maximized state
        except:
            pass
            
        self.root.configure(bg="#1e1e1e")

        # Set up the UI components
        self._setup_ui()

        # Subprocess management
        self.process = None
        self.output_queue = queue.Queue()
        self.is_running = False

        # Start the CLI process
        self.start_cli()

        # Start the periodic GUI update for output
        self.root.after(100, self.update_chat)

    def _setup_ui(self):
        # Chat/Console window (Scrollable Text)
        self.chat_window = scrolledtext.ScrolledText(
            self.root, 
            state='disabled', 
            bg="#1e1e1e", 
            fg="#d4d4d4", 
            insertbackground="white",
            font=("Consolas", 11),
            padx=10,
            pady=10,
            borderwidth=0,
            highlightthickness=0
        )
        self.chat_window.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Bottom frame for input
        self.input_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.input_frame.pack(padx=10, pady=(0, 10), fill=tk.X)

        # Input text field
        self.input_field = tk.Entry(
            self.input_frame, 
            bg="#2d2d2d", 
            fg="#d4d4d4", 
            insertbackground="white",
            font=("Consolas", 11),
            borderwidth=1,
            relief=tk.FLAT
        )
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
        self.input_field.bind("<Return>", lambda e: self.send_command())
        self.input_field.focus_set()

        # 'Say' button
        self.say_button = tk.Button(
            self.input_frame, 
            text="Say", 
            command=self.send_command,
            bg="#007acc",
            fg="white",
            activebackground="#005a9e",
            activeforeground="white",
            relief=tk.FLAT,
            padx=20,
            font=("Segoe UI", 10, "bold")
        )
        self.say_button.pack(side=tk.RIGHT, padx=(10, 0))

    def start_cli(self):
        """Initializes and starts the gemini CLI subprocess."""
        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            
            # shell=True is often necessary on Windows to find commands in PATH or aliases
            self.process = subprocess.Popen(
                ["gemini"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False, # Use binary mode for unbuffered
                bufsize=0,   # Unbuffered
                shell=True,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            self.is_running = True
            
            # Start a background thread to read from the subprocess stdout
            threading.Thread(target=self._read_stdout, daemon=True).start()
            self.append_to_chat("System: Gemini CLI session started.\n" + "-"*40 + "\n")
        except Exception as e:
            self.append_to_chat(f"System Error: Could not start gemini CLI. {e}\n")

    def _read_stdout(self):
        """Reads output from the subprocess and puts it into a queue."""
        try:
            while True:
                # Read 1 byte at a time
                chunk = self.process.stdout.read(1)
                if not chunk:
                    break
                try:
                    char = chunk.decode('utf-8', errors='replace')
                    self.output_queue.put(char)
                except Exception:
                    pass
        except Exception as e:
            self.output_queue.put(f"\n[Error reading output: {e}]\n")
        finally:
            self.is_running = False
            if self.process:
                self.process.stdout.close()
            self.output_queue.put("\nSystem: Gemini CLI session terminated.\n")

    def update_chat(self):
        """Checks the queue for new output and updates the chat window."""
        try:
            while True:
                line = self.output_queue.get_nowait()
                self.append_to_chat(line)
        except queue.Empty:
            pass
        finally:
            # Schedule the next check
            self.root.after(50, self.update_chat)

    def send_command(self):
        """Sends the user input to the CLI subprocess."""
        cmd = self.input_field.get()
        if not cmd:
            return

        # Clear the input field immediately
        self.input_field.delete(0, tk.END)

        if self.is_running and self.process and self.process.poll() is None:
            try:
                # We don't manually append the command here if the CLI echoes it back,
                # but usually we want to see what we sent.
                # However, Gemini CLI usually provides its own prompts.
                # To mimic a terminal, we might want to see the input.
                self.append_to_chat(f"\nUser: {cmd}\n")
                
                self.process.stdin.write((cmd + "\n").encode('utf-8'))
                self.process.stdin.flush()
            except Exception as e:
                self.append_to_chat(f"\nSystem Error: Could not send command. {e}\n")
        else:
            self.append_to_chat("\nSystem: Process is not running. Please restart the application.\n")

    def append_to_chat(self, text):
        """Appends text to the chat window and scrolls to the bottom."""
        self.chat_window.config(state='normal')
        self.chat_window.insert(tk.END, text)
        self.chat_window.see(tk.END)
        self.chat_window.config(state='disabled')

if __name__ == "__main__":
    root = tk.Tk()
    app = GeminiCLIWrapper(root)
    
    # Handle window close
    def on_closing():
        if app.process and app.process.poll() is None:
            app.process.terminate()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
