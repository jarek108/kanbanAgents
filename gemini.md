# Kanban CLI Tools & Integration

This project is integrated with `vibe-kanban` to manage tasks autonomously. 
HUMAN can run the server with: 
`$env:HOST="127.0.0.1"; $env:PORT="61154"; npx -y vibe-kanban`

## ⚠️ Core Architecture (MCP)

This project natively uses the Model Context Protocol (MCP) to interact with the board. 

### How Agents Should Interact with the Board
As an AI Agent (Gemini CLI), you do **not** need to run custom python scripts to interact with the board. You have native access to the `vibe-kanban` MCP server tools. 

Use the built-in MCP tools prefixed with `mcp_vibe-kanban_` to read and modify the board:
- `list_projects`: Get all project UUIDs.
- `list_issues`: Fetch tasks for a specific project.
- `create_issue`: Create a new task.
- `update_issue`: Update task status (e.g., moving to 'Done') or description.

### Headless Orchestration
The system uses Windows ConPTY for internal hosting of agent processes, ensuring zero UI flickering and robust background monitoring.

- **Engine Core**: `core/engine_pty.py` (ConPTY hosting)
- **Worker Core**: `core/engine_worker.py` (Task polling and state management)
- **Artifacts**: Artifact-driven transitions are enforced via `core/headless_gemini.py`.