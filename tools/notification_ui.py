import customtkinter as ctk
import threading
import time

class ScreenshotNotification:
    def __init__(self, message, duration=3000):
        self.message = message
        self.duration = duration
        # Run the UI in a separate thread to avoid blocking the listener
        threading.Thread(target=self._show, daemon=True).start()

    def _show(self):
        root = ctk.CTk()
        root.withdraw() # Hide main window

        # Configure notification window
        note = ctk.CTkToplevel(root)
        note.overrideredirect(True) # No title bar
        note.attributes("-topmost", True)
        note.attributes("-alpha", 0.0) # Start transparent for fade-in
        
        # Styling
        note.configure(fg_color="#1e1e1e")
        
        label = ctk.CTkLabel(
            note, 
            text="📸 " + self.message, 
            font=("Segoe UI", 12, "bold"),
            text_color="#ffffff",
            padx=20,
            pady=10
        )
        label.pack()

        # Position in bottom right corner
        note.update_idletasks()
        width = note.winfo_width()
        height = note.winfo_height()
        
        screen_width = note.winfo_screenwidth()
        screen_height = note.winfo_screenheight()
        
        # 20px padding from edges
        x = screen_width - width - 20
        y = screen_height - height - 60 # Above taskbar
        
        note.geometry(f"{width}x{height}+{x}+{y}")

        # Fade in
        for i in range(11):
            note.attributes("-alpha", i / 10)
            time.sleep(0.02)

        # Auto-destroy after duration
        def fade_out():
            for i in range(10, -1, -1):
                note.attributes("-alpha", i / 10)
                time.sleep(0.02)
            root.destroy()

        note.after(self.duration, fade_out)
        root.mainloop()

def show_notification(message, duration=3000):
    ScreenshotNotification(message, duration)

if __name__ == "__main__":
    # Test
    show_notification("Screenshot saved to artifacts!")
    time.sleep(4)
