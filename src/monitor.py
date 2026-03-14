import time
from pathlib import Path
from bus import EventBus
from events import TaskDetected

class Monitor:
    def __init__(self, bus: EventBus, watch_dir: Path):
        self.bus = bus
        self.watch_dir = watch_dir
        self._seen_files = set()

    def scan(self):
        """One-time scan of the directory for new task files."""
        if not self.watch_dir.exists():
            return

        for file_path in self.watch_dir.glob("*.md"):
            if file_path not in self._seen_files:
                # Basic check if it's an implementation request
                if "ID: IRQ-" in file_path.read_text(encoding='utf-8'):
                    self.bus.emit(TaskDetected(path=file_path.absolute()))
                    self._seen_files.add(file_path)

    def watch(self, interval: int = 5):
        """Continuous watch loop."""
        print(f"Monitoring {self.watch_dir} for new tasks...")
        try:
            while True:
                self.scan()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("Monitor stopped.")
