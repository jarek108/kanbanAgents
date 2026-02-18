# Kanban CLI Tools

CLI tools for interacting with a local Kanban API (at `http://192.168.1.185:61154`).
HUMAN can run it with (do not do this automatically): $env:HOST="0.0.0.0"; $env:PORT="61154"; npx vibe-kanban

## Tools Overview

### `list_projects.py`
Lists all available projects and their UUIDs.

### `get_tasks.py`
Fetches and displays tasks for a project. 
- **Defaults**: Project `hexArena`, Recipient `ALL`, Presentation `medium`.
- **Modes**: `--minimal` (one-liner), `medium` (default), `--full-presentation` (includes description).
- **Filtering**: `--recipient [Name]` to filter tasks.

### `monitor_project.py`
Real-time monitoring of project changes.
- **Features**: Detects new/updated/deleted tasks, shows colorized diffs for description changes.
- **Highlights**: Highlights tasks assigned to the monitored user (default `Manager`) in GREEN.
- **Sorting**: Lists user-assigned tasks first on startup.

### `orchestrator_pty.py` (New)
Full internal hosting Orchestrator using Windows ConPTY.
- **Features**: No dependency on external windows; zero UI flickering; robust background monitoring.
- **Usage**: `python tools/orchestrator_pty.py`

## Usage Examples

```bash
# List all projects
python tools/list_projects.py

# Monitor default project for Manager
python tools/monitor_project.py

# Get tasks assigned to 'Coder-ID' in minimal format
python tools/get_tasks.py hexArena --recipient Coder-ID --minimal
```