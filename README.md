# Kanban Agents

> **Scaling AI coding through artifact-driven workflows, strict Git discipline, and deterministic state machines.**

An autonomous orchestrator and toolkit for connecting AI coding agents (like Gemini CLI) to a local Kanban board for task management, bug tracking, and automated development cycles.

---

## 🎯 The Vision: Escaping the "Terminal Babysitting Trap"

A year ago, “AI-assisted coding” mostly meant autocomplete. Now we have CLI agents that will happily churn through tasks: edit files, run commands, open PRs, “fix” errors, and explain everything with conviction.

However, as agents get more capable, **human attention becomes the bottleneck**. If an agent drifts, it doesn't drift politely—it drifts into refactors, drive-by changes, and architectural violations that turn a 20-minute task into a three-hour whack‑a‑mole cycle. If a system is “productive” only when an engineer is continuously monitoring terminal output, diff-by-diff, then it isn’t scaling engineering—it’s just relocating the work into a higher-stress form of supervision.

**The strategic pivot: limit freedom to increase capability.**
The way to make agents *more useful* is to make them *less free* through **hard workflows**. 

This project treats “agentic coding” like a controlled production line. The project is a workflow graph (states + transitions). Every transition requires specific Markdown **artifacts** (e.g., specifications, implementation reports, QA results). No artifact, no transition. Wrong artifact, no transition. The orchestrator enforces the rules; agents produce the artifacts.

*(Read the full manifesto in [`docs/notes/01_vision_and_philosophy.md`](docs/notes/01_vision_and_philosophy.md))*

---

## 🏗️ Core Architecture

This project strictly separates the human coordination layer from the physical execution layer:

1. **The Control Plane (`vibe-kanban`):** 
   A web-based Kanban board acting as the human interface and global source of truth. It manages projects, issues, tags, and dependencies. It features a built-in React Flow **dependency graph** for visualizing complex task blockages. It exposes its data to agents natively via the Model Context Protocol (MCP).
2. **The Execution Plane (`kanbanAgents`):** 
   A local Python orchestrator that runs on the developer's machine. It spawns, monitors, and manages autonomous `gemini-cli` workers using OS-level pseudoconsoles (ConPTY). It enforces Git branching policies, watches the filesystem for artifact triggers, and updates the Kanban board automatically.
3. **The Artifacts:** 
   Markdown contracts (`IRQ-*.md`, `IRP-*.md`, `QRP-*.md`) that serve as the single source of truth for an agent's intent, execution, and verification.

---

## 🚀 Quick Start (Getting the Engine Running)

### 1. Prerequisites
- **Node.js** (and `npm` / `pnpm`)
- **Python 3.10+** (for the local orchestrator)
- **Git**
- **Rust & C/C++ Build Tools** (Automatically handled by the bootstrapper for the backend DB/MCP server)
- **Gemini CLI** (Installed globally)

### 2. Start the Kanban Control Plane
Open a terminal in the project root and run the unified cross-platform bootstrapper. This script will download the `vibe-kanban` frontend/backend, install required OS-level C++ compilers/LLVM, build the project, and start the local server on port `61154`.

**Windows:**
```cmd
.\start_board.bat
```

**macOS / Linux:**
```bash
./start_board.sh
```

### 3. Start the Local Orchestrator
In a separate terminal, launch the local Python orchestrator to manage your AI workers:
```bash
python legacy_client_ui/app.py
```
*(Note: You can pass `--reset-position` if the Tkinter window spawns off-screen).*

### 4. Custom Gemini Commands
This repository includes a `.gemini/` capability bundle containing custom macros. For example, use `/perp <query>` in your active Gemini CLI session to seamlessly trigger an automated Playwright web scraper that performs deep research on Perplexity.ai and injects the findings directly into your context window.

---

## 📂 Repository Structure

The codebase is highly modularized, strictly isolating legacy UI from the headless core:

*   `/core` - Reusable, headless workflow engines (`engine_pty.py`, `engine_kanban.py`).
*   `/docs` - Specifications, architectural theory, and Markdown artifact templates.
*   `/scripts` - Standalone automation tools (e.g., `gemini.exp`, `research_perplexity.py`).
*   `/legacy_client_ui` - The Tkinter desktop app for visualizing ConPTY streams, quarantined for planned retirement as we move to a pure event-bus architecture.

---

## 🗺️ What's Next?
*   Transitioning from the `legacy_client_ui` to a pure, headless Python event-bus architecture (see `docs/notes/02_architecture_v2.md`).
*   Expanding MCP integration to allow agents to natively reason about Git branching policies.
