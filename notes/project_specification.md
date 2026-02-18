# Project Specification: Kanban-Driven Agent Orchestration

## **1. Project Overview**
The goal of this project is to create a distributed system for managing autonomous AI agents (Gemini-CLI Workers) using a centralized Kanban board. The system enables a "Human-in-the-loop" workflow where a Central Service tracks task states, and local Machine Orchestrators manage the physical execution, Git discipline, and terminal monitoring of agents.

---

## **2. Component A: Centralized Kanban Service**
A web-based platform serving as the global source of truth for project status and task assignments.

### **MUST**
- **Web Interface**: Browser-accessible dashboard for viewing and moving tasks across columns (Backlog, To Do, In Progress, QA, Done).
- **REST/WebSocket API**: Allow local Orchestrators to register themselves, fetch tasks, and update card statuses.
- **Metadata Storage**: Store links to specific artifacts (e.g., "IRQ-001.md") and the machine ID where the worker is active.
- **Multi-User Support**: Allow different humans to interact with the board simultaneously.

### **NICE TO HAVE**
- **Real-time Event Streaming**: Push updates to Orchestrators immediately when a card is moved in the browser.
- **Artifact Preview**: Ability to read Markdown reports (IRP, QRP) directly in the web UI.

### **MUST NOT**
- **Machine-Specific Logic**: The central service must not know *how* to run a worker, only *that* a worker is running.

---

## **3. Component B: Machine Orchestrator (Local Controller)**
A local application (Standalone or IDE Extension) that bridges the Central Service with the local OS and file system.

### **MUST**
- **Worker Lifecycle Management**: Spawn, monitor, and kill `gemini-cli` worker instances.
- **Interactive Terminal Host**: Provide a fully functional terminal environment (ConPTY) for every worker, allowing human takeover/inspection.
- **File System Monitoring**: Watch project folders for the appearance of specific artifacts (`IRQ`, `IRP`, `QAR`, `QRP`) to trigger state transitions.
- **Git Enforcement**: 
    - Automatically create task branches.
    - Lock workers to a specific branch (kill/alert if worker attempts to `git checkout` elsewhere).
- **Kanban Sync**: Continuous polling/updating of the Central Service based on local events (e.g., "Artifact produced" -> "Update Status to QA").
- **Multi-Worker Monitoring**: Dashboard-style view of all local PTYs with the ability to "zoom in" on one for interaction.

### **NICE TO HAVE**
- **VS Code Extension Integration**: Live inside the editor to utilize the native Terminal and File Explorer.
- **Resource Limiting**: Cap CPU/Memory usage per worker.

### **MUST NOT**
- **Credential Storage**: Must not store hardcoded API keys; use environment variables or local secret stores.

---

## **4. Component C: Gemini-CLI Workers**
The autonomous agents executing the work.

### **MUST**
- **Kanban Awareness**: Pick up tasks assigned to their role (Manager, Coder, QA) via the Orchestrator.
- **Artifact Production**: Generate standardized Markdown files for reports and requests as defined in `flow.md`.
- **Persistence**: Capability to stay alive and wait for the next command/artifact to appear in their linked folder.
- **Shell Access**: Capability to execute commands, read files, and use Git within the Orchestrator's constraints.

### **NICE TO HAVE**
- **Self-Correction**: Detect when a command fails and attempt an alternative before escalating.

### **MUST NOT**
- **Branch Hopping**: Must not attempt to merge or switch branches unless explicitly instructed by the Orchestrator's workflow rules.

---

## **5. Formal Orchestration Rules (State Machine)**
Based on `flow.md`, the Orchestrator enforces the following transitions:

1.  **Drafting Stage**: 
    - *Trigger*: Card moved to "In Progress" with role "Manager".
    - *Action*: Orchestrator ensures Manager worker is on `main` or a `feature/` branch.
2.  **Implementation Handoff**:
    - *Trigger*: Appearance of `IRQ-*.md` in the project folder.
    - *Action*: Orchestrator moves card to "Coder," creates `task/IRQ-ID` branch, and signals the Coder worker.
3.  **QA Loop**:
    - *Trigger*: Appearance of `IRP-*.md`.
    - *Action*: Orchestrator moves card to "QA," signals QA worker.
    - *Branch Transition*: If QA status is `to correct`, move back to Coder. If `final`, move to Manager for closure.
4.  **Escalation**:
    - *Trigger*: Artifact content contains `Status: blocked` or `Status: needs info`.
    - *Action*: Orchestrator alerts the Human and moves the card to a "Blocked" column.

---

## **6. Future Goals**
- **Multi-Machine Orchestration**: A single human can manage workers across a local PC, a remote server, and a cloud VM from one Central Kanban.
- **Dynamic Role Definitions**: Load new `agent_definitions/*.md` on the fly without restarting the Orchestrator.
