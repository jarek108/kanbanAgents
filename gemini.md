# Kanban CLI Tools & Integration

This project is integrated with `vibe-kanban` to manage tasks autonomously. 
HUMAN can run the server with (do not do this automatically): 
`$env:HOST="127.0.0.1"; $env:PORT="61154"; npx -y vibe-kanban`

## ⚠️ Important Architecture Change (MCP)

**The old Python REST API tools (`tools/list_projects.py`, `tools/get_tasks.py`, `tools/engine_kanban.py`) are DEPRECATED and BROKEN.** The newer versions of `vibe-kanban` no longer expose a REST JSON API at `/api/projects`.

**Instead, this project natively uses the Model Context Protocol (MCP).**

### How Agents Should Interact with the Board
As an AI Agent (Gemini CLI), you do **not** need to run custom python scripts to interact with the board. You have native access to the `vibe-kanban` MCP server tools. 

Use the built-in MCP tools prefixed with `mcp_vibe-kanban_` to read and modify the board:
- `list_projects`: Get all project UUIDs.
- `list_issues`: Fetch tasks for a specific project.
- `create_issue`: Create a new task.
- `update_issue`: Update task status (e.g., moving to 'Done') or description.

### `orchestrator_pty.py`
Full internal hosting Orchestrator using Windows ConPTY.
- **Features**: No dependency on external windows; zero UI flickering; robust background monitoring.
- **Usage**: `python tools/orchestrator_pty.py`