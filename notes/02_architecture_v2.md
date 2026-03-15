# **1. Project Overview**
This project implements Kanban-Driven Agent Orchestration for reliable AI-assisted software engineering ('vibe-coding'), addressing the issues below.

## Problem Statement
Coding agents have improved in raw capability and usability, but their productivity in long-running, real-world engineering workflows is still unreliable and poorly integrated with human processes. Brittle performance shifts the coordination and verification burden onto a key bottleneck: human cognitive capacity. The key issues include:

* **I 1. Scope drift and constraint violations**: Agents often implement beyond the requested change or violate architectural constraints/invariants, causing cascading fixes and reducing trust; prompt-stated constraints aren’t reliably enforceable during implementation.

* **I 2. Workflow violations**: Policies (e.g. review, QA, testing, or version control) are also fragile. Agents not restricted by explicit workflows and gating criteria undermine consistency and quality by inducing merges without testing, skipped reviews, inconsistent branching etc.

* **I 3. Granularity shift and escalation management problem**: Lack of systematic tools to move from code-level intervention to architectural intent or project-wide status (or return when escalation is critical), combined with scope/workflow violations keep the user stuck in low-level implementational-level babysitting.

* **I 4. Context fragmentation and cognitive overload**: Diverging contexts are easily disconnected with multiple plans, attempts, explanations and partial implementations with unclear coherence, especially in multi-agent setups. User becomes the critical bottleneck trying to supervise and reconcile the inconsistencies.

* **I 5. Informal quality control**: Review/QA tends to be optional and leaky in separation-of-duties (the same model/process implements and validates), so it becomes “best effort” rather than a first-class, enforceable stage with effective checks.

* **I 6. Role/prompt explosion doesn’t scale**: Ad-hoc addition of agent roles/prompts used to improve performance in the short-term increases the human coordination burden in the long-term (more context switching, handoffs, reconciliation of conflicting outputs), reducing predictability and often lowering productivity over time.

* **I 7. Disconnection from human collaboration workflows**: Coding-agent usage doesn’t map cleanly onto multi-human processes: shared Kanban status, handoffs, reviews/approvals, or traceable decision history. This makes collaboration and adoption difficult beyond a single operator who is burdened as a gateway between agent(s) and human collaborators.

## Strategic Directions
We define two tightly linked strategic direction areas: agent-centric integrity controls and human-centric attention management.

**SD 1 Integrity Enforcement via Agent Control.** It is essential to selectively limit agent autonomy to contain typical LLM unreliability and workflow violations. Specifically:

* **SD 1.1 Mechanically Enforced Workflows**: Force agents to operate within a rigid, graph-based execution environment to mechanically enforce valid state transitions, rather than relying on prompt compliance.

  <details> <summary> More details...</summary> 

  *Prevent invalid transitions such as merging without required approvals, bypassing required checks/tests, or moving work to the wrong branch/state*

  </details>

* **SD 1.2 Artifact-Centric Task Status**: Make agent work artifact-centric to ensure a single source of truth (validated artifacts) and auditable progress. 

Added: Assumed artifact format enforces completness of the data required by the agent consuming the artifacts serving as a strong contract definition.

  <details> <summary> More details...</summary> 

  *Canonical artifacts like feature specification, implementation report, QA report make task statuses unambiguous.*

  </details>

* **SD 1.3 Bounded Task Scope & Architectural Constraints**: Bound the allowed change surface per task explicitly (what may be modified) and enforce architectural invariants (what must remain true) via automated checks to prevent regressions and unintended redesign. 

  <details> <summary> More details...</summary> 

  *Active enforcement of formal implementation constraints, not just coding agent prompting, is necessary to prevent rogue systemic changes to implement minor features, or cascades of unforeseen redesigns in response to minor failures.*

  </details> 

* **SD 1.4 Adversarial Separation of Duties**: Enforce quality and constraint adherence via adversarial role separation—splitting execution and verification across independent contexts to prevent self-validation bias. 

  <details> <summary> More details...</summary> 

  *Separating information and goals between independent or adversarial agent pairs ('Planner vs Doer', 'Maker vs Checker') addresses LLM issues with leaky coding-testing separation, silent scope changes during implementation.*

  </details>

**SD 2 Human Attention Management & Cognitive Load Minimization** *Human attention is the crucial limited resource that needs to be spent on essential decisions, not low-level details.*

* **SD 2.1 Traditional Human-Centric Interaction Surfaces**: Integrate agents into the same collaboration surfaces (Kanban, Git, and documentation/specs) to lower interaction cognitive cost and facilitate multi-user collaborations.  

  <details> <summary> More details...</summary> 

  *Integrating agents into the same human collaboration surfaces makes their work legible and multi-user by default: planning and status live in Kanban, change intent and implementation live in Git/PRs, and decision history lives in the same artifact trail the team already uses. 
  
  Instead of introducing a parallel “agent UI,” the system should map agent actions onto familiar primitives (cards, branches, commits, PRs, check results, approvals) so humans can review, approve, and hand off work using existing habits and permissions. 
  
  This also avoids role/prompt sprawl by forcing coordination through shared objects rather than private conversations with each agent.*

  </details>

* **SD 2.2 Prioritized Project-level Focus**: Shift the primary user interaction to project-level task specification and monitoring to avoid getting stuck in implementation babysitting. 

  <details> <summary> More details...</summary> 

  *The default user posture should be “portfolio/task-level control,” not terminal supervision: specify intent and acceptance criteria, monitor progress, and approve stage transitions via the Manager/Kanban view. 
  
  Drill-down into implementation (logs, diffs, terminals) should be optional and exception-driven, triggered by escalation signals (stalls, repeated retries, plan divergence) rather than by routine curiosity. 
  
  This keeps attention focused on a small number of high-leverage decisions (scope, priority, constraints, acceptance) while still preserving the ability to zoom in quickly when necessary.*

  </details>

* **SD 2.3 Assisted Work Planning**: Make the Manager Agent a planning partner to support intent clarification and work decomposition, then compile decisions into workflow-required artifacts actionable by execution agents. 

  <details> <summary> More details...</summary> 
  
  *This applies to working out feature shape, work decomposition, prioritization, implementation approach, and architectural constraints. 
  
  User works out intent with the Manager Agent, which proposes high-confidence defaults (auto-filling routine choices) and converts uncertainty into explicit decisions; identifies missing information, implicit assumptions, and unclear constraints; surfaces decision points the user may have missed; and helps compare trade-offs until intention can be compiled into formal, workflow-required artifacts for execution agents. *
  
  </details>

* **SD 2.4 Assisted Outcome Consumption & Monitoring**: Make the Manager Agent a monitoring and interpretation partner to turn evolving multi-agent work streams into decision-ready status, surface emergent risks and decision points, and guide the user through exploration of task states (done/WIP/blocked/failed) without requiring raw log-level inspection. 

  <details> <summary> More details...</summary> 
  
  Monitoring multi-agent task execution across evolving plans, adversarial handoffs, partial outputs, and directional changes can face the user with overwhelming amounts of information. Instead, the user explores outcomes with the Manager Agent, which synthesizes streams of agent activity into a coherent narrative; summarizes deltas since the last check-in; links claims to supporting artifacts/log excerpts; flags newly introduced assumptions, scope changes, and emergent decision points; and distinguishes normal variance from policy violations or regressions.
  
  It supports guided drill-down from portfolio → task → stage → evidence so the user can quickly understand whether work is done, WIP, blocked, or failed, and what action (approve, clarify, re-scope, escalate, or intervene) is required—without reading raw transcripts end-to-end. </details>

* **SD 2.5 Failure Observability & Intervention Paths**: Detect and escalate failures (non-converging maker–checker loops, material plan divergences) with low-noise, actionable alerts that trigger a guided drill-down to the implementation layer only when intervention is required. Present evidence-linked, decision-ready context to enable rapid, targeted, assisted action on the appropriate level: feature specification, task decomposition, architecture, implementation, or testing.

  <details> <summary> More details...</summary> 
  
  User must be able to trust task statuses. Failures should be observable as divergence or non-convergence, not as silent progression: repeated maker–checker cycles without net progress, oscillating patches, chronic test/quality gate failures, or implementation changes that depart from the agreed feature/architecture intent.
  
  Escalation must be low-noise and policy-driven (rate limits, retry budgets, divergence thresholds) so the user is interrupted only when a decision or intervention is actually required. 
  
  When escalation triggers, the Manager Agent presents guided, decision-ready context with links to evidence: current stage/state, attempt trajectory, last known-good artifacts, guided diffs, diagnosis, and supporting evidence (e.g. whether the deviation is spurious or justified by new low-level discoveries), and a small set of explicit options (approve re-scope/re-plan, adjust constraints, request targeted fixes, or force rollback/retry).
  
  Guided drill-down should support jumping to the appropriate layer—specification, decomposition, architecture, implementation, or testing—without requiring full transcript review. 
  
  </details>

## Core Design Principles


move to design principles? ->via explicit MUST/MUST NOT contracts

move to design principles: ' Coder vs QA roles; plus explicit “MUST / MUST NOT” contracts embedded in manager↔worker artifact exchange.'?

- **Hard Workflow Graphs**: Workflow Definitions (WFDs) define rigid state machines where transitions only occur when mandatory artifacts appear and pre-conditions are met. No out-of-order execution, no skipping stages—the system enforces the graph strictly.
- **Machine-Local Orchestration**: Each machine runs an Orchestrator that spawns, monitors, and manages agent processes. Orchestrators enforce Git discipline, track artifact production, validate state transitions, and provide a live terminal interface for operator inspection.
- **Artifact-Driven State Flow**: Tasks progress through workflow states only when agents produce required artifacts (Markdown files) matching expected patterns. Artifacts become the single source of truth for state and transition eligibility.

- ** Reuse of human-friendlytools **. Kanban, Git or documentation (feature request specification) are both tested and familiar solutions to these problems. 

- **Multi-Layer Control**: Three distinct UIs provide control and visibility—Kanban browser interface for global project breakdown and task assignment, local Orchestrator app for live worker status and terminal interaction, and Git repository as the artifact store and branch workspace controller. A Manager Agent serves as the sole intelligent contact point, interpreting Kanban state and orchestrating planning.
- **Stateless State Persistence**: The Orchestrator is generic and data-driven; all workflow logic resides in the WFD schema loaded at runtime. Agent roles, branching rules, transition conditions, and artifact expectations come entirely from the active workflow definition—enabling reusable, pluggable processes.
---



Here is the list of recommended documentation areas with their associated priorities. The Project Overview should strictly limit itself to defining the scope and core philosophy of these areas, not their mechanics. It serves as the "What" and "Why," while the detailed sections serve as the "How."

Priority: MUST
- Agent Lifecycle & Supervision: Resource allocation, health monitoring, crash recovery, graceful shutdown.
- Workflow Enforcement Constraints: No skip-ahead, rollback mechanisms, conflict detection on multi-agent transitions.
- Artifact Schema & Validation: Version history tracking, dependency resolution, cleanup policies.
- Git Integration Strategy: Branch lifecycle management, merge strategy, cross-machine sync, commit validation.
- Manager Agent Responsibilities: Planning, blockage detection, dynamic workflow adjustment, status summarization.
- Security & Isolation: Agent context sandboxing, Git credential management, prompt injection prevention.

Priority: NICE TO HAVE
- Orchestrator Discovery & Coordination: Machine registry, Orchestrator-to-Orchestrator messaging for distributed scenarios.
- Monitoring & Observability: Execution traces, decision logs, state audit trail, performance metrics.
- Error Recovery & Resilience: Timeout recovery, artifact validation failure handling, consistency guarantees.
- Handle multi-agent/prompt explosion: Keep coordination and context overhead bounded by defaulting to a small universal workflow (e.g., 3 roles) while still allowing controlled extensions and modifications when justified.

# **2. Core Concept: The Workflow Engine**
The heart of the system is the **Workflow Definition (WFD)**. A WFD defines:
- **Roles**: Logical participants in the flow (e.g., Architect, Coder, Reviewer).
- **States**: The stages of a task (corresponds to Kanban columns).
- **Transitions**: The logic that moves a task between states.
- **Artifacts**: Mandatory files produced/consumed at each transition.
- **Policies**: Git branching rules and shell restrictions for each role/state.

---

# **3. Component A: Centralized Kanban & Registry Service**
## **MUST**
- **Unified Board**: Browser UI that reflects the current state of all projects and workflows globally.
- **Workflow Registry**: Store and serve versioned Workflow Definitions (WFDs) to local Orchestrators.
- **Global Identity**: Track which Machine ID is currently hosting which specific Worker for a task.

## **NICE TO HAVE**
- **Flow Visualizer**: Interactive DAG (Directed Acyclic Graph) view of the active workflow.
- **Artifact Explorer**: Deep integration with Markdown artifacts (diffs, version history).

---

# **4. Component B: Generalized Machine Orchestrator**
The Orchestrator is no longer "3-agent aware." It is a **State Machine Runner**.

## **MUST**
- **Dynamic Role Binding**: Launch workers based on the Roles defined in the active WFD (e.g., "Role: Reviewer" spawns a Gemini-CLI with the `reviewer.md` prompt).
- **Artifact-Triggered Transitions**: Monitor the workspace for specific filenames or content patterns (e.g., "If `IRP-*.md` appears and contains `Status: ready`, move to `QA` state").
- **State-Aware Git Management**: 
    - Enforce branching patterns (e.g., `feature/`, `fix/`, `qa/`) based on the current state.
    - Prevent "Ghost Commits" (workers committing to the wrong branch).
- **Interactive PTY Multi-Tenancy**: Host multiple interactive terminal sessions simultaneously, providing a "Command Center" view for the human operator.
- **Local Flow Persistence**: Save and resume the state of a flow even if the Orchestrator or workers are restarted.

## **MUST NOT**
- **Hardcoded Logic**: No "Manager/Coder/QA" logic should be in the Orchestrator code. It must all be loaded from the WFD.

---

# **5. Component C: Gemini-CLI Workers (Agents)**
## **MUST**
- **Prompt Injection**: Receive their role-specific instructions (`agent_definitions/*.md`) at spawn time.
- **Orchestrator API Hook**: Standardized way to "Submit Artifact" or "Signal Blockage" to the local Orchestrator.
- **Context Awareness**: Ability to read the current "Task Metadata" (which branch they are on, what the preceding artifact was).

---

# **6. Reference Implementation: The "Classic 3-Agent Flow"**
A valid WFD for our initial use case would look like this (conceptual):

```yaml
Workflow: Classic-Development
Roles: [Manager, Coder, QA]
States:
  - Name: Discovery
    Owner: Manager
    Exit_Trigger: Created(IRQ-*.md)
    Next_State: Implementation

  - Name: Implementation
    Owner: Coder
    Git_Policy: NewBranch(task/ID)
    Exit_Trigger: Created(IRP-*.md)
    Next_State: Validation

  - Name: Validation
    Owner: QA
    Exit_Trigger: Content(QRP-*.md, "Status: final") -> Done
    Retry_Trigger: Content(QRP-*.md, "Status: to_correct") -> Implementation
```

---

# **7. Must/Nice/Must Not Recap**

| Feature | MUST | NICE TO HAVE | MUST NOT |
| :--- | :--- | :--- | :--- |
| **Workflows** | Pluggable/Data-driven | Hot-reloading of rules | Hardcoded state logic |
| **Git** | Automated branching | Conflict auto-resolution | Unrestricted branch access |
| **Terminal** | Full Interaction (ConPTY) | Remote Terminal Access | Log-only (non-interactive) |
| **Artifacts** | Markdown-based | JSON Schema validation | Proprietary binary formats |
| **Scale** | Multi-worker/Machine | Cloud-native deployment | Single-machine only |
