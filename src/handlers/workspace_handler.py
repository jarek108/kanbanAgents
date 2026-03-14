from pathlib import Path
from bus import EventBus
from events import RequestWorkspace, WorkspaceReady

class WorkspaceHandler:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.bus.subscribe(RequestWorkspace, self.on_request)

    def on_request(self, event: RequestWorkspace):
        workspace_name = event.recipient
        workspace_path = event.base_workdir / workspace_name
        
        if workspace_path.exists():
            print(f"Using existing workspace: {workspace_path}")
        else:
            workspace_path.mkdir(parents=True, exist_ok=True)
            print(f"Created new workspace: {workspace_path}")
            
        self.bus.emit(WorkspaceReady(path=workspace_path))
