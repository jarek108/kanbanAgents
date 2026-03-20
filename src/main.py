import argparse
from pathlib import Path
from bus import EventBus
from pipeline import Pipeline
from monitor import Monitor
from handlers import GitHandler, WorkspaceHandler, AgentHandler
from events import TaskDetected

def main():
    parser = argparse.ArgumentParser(description="Programmatic agent workspace initializer (Event-Driven).")
    parser.add_argument("request_file", type=str, nargs='?', help="Path to the implementation_request.md (optional in monitor mode)")
    parser.add_argument("--workdir", type=str, default="workspaces", help="Base directory for workspaces")
    parser.add_argument("--push", action="store_true", help="Push the feature branch to origin")
    parser.add_argument("--watch", type=str, nargs='?', const='tasks', help="Monitor the specified directory for new requests (defaults to 'tasks')")
    
    args = parser.parse_args()
    base_workdir = Path(args.workdir).absolute()
    
    # 1. Initialize Infrastructure
    bus = EventBus()
    
    # 2. Initialize Handlers
    _git = GitHandler(bus)
    _ws = WorkspaceHandler(bus)
    _agent = AgentHandler(bus)
    
    # 3. Initialize Orchestrator
    _pipeline = Pipeline(bus, base_workdir, push_on_finish=args.push)
    
    # 4. Trigger Entry Point
    if args.watch:
        # Monitor mode
        watch_dir = Path(args.watch).absolute()
        monitor = Monitor(bus, watch_dir)
        monitor.watch()
    elif args.request_file:
        # CLI single file mode
        request_file_path = Path(args.request_file).absolute()
        if not request_file_path.exists():
            print(f"Error: {request_file_path} not found.")
            return
        
        print(f"Starting pipeline for {request_file_path}...")
        bus.emit(TaskDetected(path=request_file_path))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
