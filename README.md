# Kanban Agents

An autonomous orchestrator and toolkit for connecting AI coding agents (like Gemini CLI) to a local Kanban board for task management, bug tracking, and automated development cycles.

## 🚀 Setup & Installation (New Computer)

To set up the `vibe-kanban` server on a new machine, follow these steps. The project relies on Node.js to run the local Kanban board and the Model Context Protocol (MCP) to connect AI agents to it.

### 1. Prerequisites
- **Node.js** (and `npm` / `npx`) must be installed.
- **Git** (to clone this repository).
- **Gemini CLI** (or another MCP-compatible AI agent).

### 2. Start the Kanban Server
Open a terminal and run the following command to download and start the local web application:
```bash
npx -y vibe-kanban
```
This will start the local web UI and backend. It usually opens your browser automatically.

**Specific Port/IP Requirement:**
If your AI orchestrator relies on a specific port (like `61154`), run the server with environment variables:
- **Windows (PowerShell):**
  ```powershell
  $env:HOST="127.0.0.1"; $env:PORT="61154"; npx -y vibe-kanban
  ```
- **macOS / Linux:**
  ```bash
  HOST=127.0.0.1 PORT=61154 npx -y vibe-kanban
  ```

### 3. Connect AI Agents (Gemini CLI)
This project is pre-configured to automatically connect the Gemini CLI to the `vibe-kanban` server via the Model Context Protocol (MCP).

1. Clone this repository to your new machine.
2. Open a terminal inside the project folder (`kanbanAgents`).
3. Start your Gemini CLI session.
4. The CLI will automatically read the `.gemini/settings.json` file, initialize `vibe-kanban mcp` in the background, and seamlessly bind all the board management tools (e.g., `list_projects`, `create_issue`, `update_issue`).

You are now ready to have AI agents read, write, and manage tasks autonomously!

---

## 🏗️ Architecture Note
*Legacy Notice: The previous Python wrappers (`tools/engine_kanban.py`, `get_tasks.py`) that relied on REST API polling (`/api/projects`) are deprecated and no longer compatible with newer versions of `vibe-kanban`. All integrations now use the native MCP standard.*
