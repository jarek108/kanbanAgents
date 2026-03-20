# Refactoring Proposal: Event-Driven Handler Architecture

This document proposes a streamlined, event-driven architecture for the agent workspace management system. The goal is to decouple the *orchestration* of workflows from the *execution* of specific tasks using a pattern of **Events** and **Handlers**.

## 1. Core Concept: Orchestrator & Handlers

The architecture separates the system into three distinct layers:
1.  **Monitoring**: Watches for triggers (new files, status changes).
2.  **Orchestration (Pipeline)**: Decides *what* should happen next based on events.
3.  **Execution (Handlers)**: Performs the actual work (Git operations, File creation).

This removes the need for a monolithic "Manager" class, replacing it with small, focused handlers that react to specific events.

---

## 2. Components

### A. The Pipeline (Orchestrator)
The central nervous system. It maintains the session state and decides the workflow sequence. It does not know *how* to clone a repo, but it knows *when* to ask for it.

**Responsibilities:**
- Wires the application (initializes Bus, Monitor, Handlers).
- Listens for `TaskDetected` and emits the sequence of setup events (`RequestGitClone`, `RequestWorkspace`).
- Coordinates the transition from "Setup" to "Coding".

### B. The Event Bus
A lightweight message broker.
- `subscribe(event_cls, callback)`
- `emit(event_obj)`

### C. The Monitor (Observer)
The eyes of the system. It strictly observes and reports; it never changes state.

**Responsibilities:**
- Watch `implementation_request.md` files.
- Monitor Agent logs/health.
- Emit `TaskDetected` or `AgentStatusChanged`.

### D. Handlers (The Doers)
Focused modules that encapsulate specific domain logic. They replace the old `utils` and `managers`.

#### 1. `GitHandler`
*Replaces `src/git_ops.py`*
- Subscribes to: `RequestGitClone`, `RequestBranch`, `RequestPush`.
- Logic: content of `git_ops.py` (run_git, clone_repo, etc.) moved here as method handlers.
- Emits: `GitReady`, `PushCompleted`.

#### 2. `WorkspaceHandler`
*Replaces `src/workspace.py`*
- Subscribes to: `RequestWorkspace`.
- Logic: directory creation and path management.
- Emits: `WorkspaceReady`.

#### 3. `AgentHandler`
*Placeholder for the Coder*
- Subscribes to: `StartCoding`.
- Logic: Spawns the coding agent process.
- Emits: `CodingFinished`.

---

## 3. Workflow & Event Flow

### Defined Events (`src/events.py`)

| Event Class | Payload | Source | Purpose |
| :--- | :--- | :--- | :--- |
| **Triggers** | | | |
| `TaskDetected` | `path` | Monitor | A new task file was found. |
| **Commands** | | | |
| `RequestWorkspace` | `task_id` | Pipeline | Ask to create folders. |
| `RequestGitClone` | `url`, `path` | Pipeline | Ask to clone repo. |
| `RequestBranch` | `name`, `base` | Pipeline | Ask to setup branch. |
| `StartCoding` | `context` | Pipeline | Handover to Agent. |
| **Signals** | | | |
| `WorkspaceReady` | `path` | WorkspaceHandler | Folder is ready. |
| `GitReady` | `current_branch` | GitHandler | Repo is checked out & ready. |
| `WorkCompleted` | `diff` | AgentHandler | Coding is done. |

### Example Flow

1.  **Monitor** sees `task.md` -> emits `TaskDetected`.
2.  **Pipeline** receives `TaskDetected`:
    -   Parses metadata.
    -   Emits `RequestWorkspace`.
3.  **WorkspaceHandler** receives `RequestWorkspace`:
    -   Creates dir.
    -   Emits `WorkspaceReady(path)`.
4.  **Pipeline** receives `WorkspaceReady`:
    -   Emits `RequestGitClone(url, path)`.
5.  **GitHandler** receives `RequestGitClone`:
    -   Runs `git clone`.
    -   Emits `GitReady`.
6.  **Pipeline** receives `GitReady`:
    -   Emits `StartCoding`.

---

## 4. Proposed File Structure

We will refactor `src/` to group logic by domain capability (handlers) rather than by technical layer (utils).

```text
src/
├── main.py                 # Entry point: Wires Bus, Handlers, starts Monitor.
├── pipeline.py             # Logic: Event coordination & state machine.
├── events.py               # Data Classes: The contract between components.
├── bus.py                  # Infrastructure: Simple EventBus.
├── monitor.py              # Logic: File watching / polling.
├── handlers/               # The "Doers"
│   ├── __init__.py
│   ├── git_handler.py      # Encapsulates git_ops logic.
│   ├── workspace_handler.py# Encapsulates workspace logic.
│   └── agent_handler.py    # Encapsulates agent running logic.
└── utils/                  # (Optional) Truly generic helpers only.
    └── parser.py           # Helper to read .md files (used by Pipeline).
```

## 5. Migration Strategy

1.  **Scaffold**: Create `src/handlers/`, `src/bus.py`, `src/events.py`.
2.  **Move Logic**: 
    -   Move functions from `src/git_ops.py` -> `src/handlers/git_handler.py` (wrap in class).
    -   Move functions from `src/workspace.py` -> `src/handlers/workspace_handler.py`.
3.  **Implement Infrastructure**: Write `src/bus.py` and `src/monitor.py`.
4.  **Implement Orchestration**: Write `src/pipeline.py` to listen to Monitor and invoke Handlers.
5.  **Switch**: Update `main.py` to run the new `Pipeline` instead of the linear script.
