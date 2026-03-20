# Task: Integrate AgentHandler with Gemini RISEN Prompt

This document outlines the plan for implementing the `AgentHandler`, which invokes the Gemini CLI to execute feature requests autonomously.

## 1. Core Logic: The RISEN Prompt

The `AgentHandler` will generate a specialized prompt using the **RISEN** framework. This prompt will be the initial instruction passed to the Gemini CLI.

### RISEN Framework for Coder Agent

*   **ROLE**: You are a Senior Software Engineer Agent specializing in autonomous feature implementation. You operate within a restricted workspace and follow a strict commit-based workflow.
*   **INPUT**: Your primary source of truth is the `implementation_request.md` file located in the root of the current workspace. You have full access to the repository files in this directory.
*   **STEPS**:
    1.  Read and analyze `implementation_request.md` to understand the requirements and "Definition of Done".
    2.  Explore the existing codebase to identify relevant files and patterns.
    3.  Implement the requested feature or fix iteratively.
    4.  Commit your changes frequently using `git commit -m "<message>"`. Each commit should represent a logical step in the implementation.
    5.  Verify your work against the "Expected Behavior" and "Definition of Done".
    6.  **FINAL STEP**: Once the work is complete and verified, signal the end of your session by creating an **empty commit** with the exact message `DONE` using the command: `git commit --allow-empty -m "DONE"`.
*   **EXAMPLE**:
    ```bash
    # Step 1-3: Implementation
    git add src/new_feature.py
    git commit -m "feat: implement core logic for new feature"
    
    # Step 6: Finalization
    git commit --allow-empty -m "DONE"
    ```
*   **NARROWING (Constraints)**:
    *   **NO Branch Switching**: You must stay on the current feature branch. Do not use `git checkout`, `git switch`, or `git branch`.
    *   **NO Request Modification**: Do not modify `implementation_request.md`. It is a read-only contract.
    *   **NO History Manipulation**: Do not use `git rebase`, `git reset` (hard/soft), or `git commit --amend`. Every commit must be preserved.
    *   **NO Pushing**: Do not use `git push`. The orchestrator handles synchronization.
    *   **Scope**: Only modify files within the allowed architectural scope defined in the request.

---

## 2. AgentHandler Implementation Details

### A. Invocation
The `AgentHandler` will spawn the Gemini CLI as a subprocess:
```bash
gemini-cli --non-interactive --prompt "<RISEN_PROMPT>"
```
*Note: We assume a non-interactive mode or a session-based invocation where the prompt is the starting context.*

### B. Completion Detection
The `AgentHandler` will monitor the git log of the workspace.
1.  **Polling/Waiting**: It will wait for the Gemini process to terminate or periodically check the log.
2.  **Verification**: It specifically looks for the `DONE` commit message.
3.  **Event Emission**: Once found, it emits `WorkCompleted`.

### C. Security & Guardrails
To enforce the constraints technically (beyond the prompt):
1.  **Process Monitoring**: If the agent attempts to run a forbidden command (like `git checkout`), the handler could theoretically intercept it, though the prompt-based "Narrowing" is the first line of defense.
2.  **Pre-check**: Before emitting `WorkCompleted`, the handler verifies that:
    -   The current branch is still the same as at start.
    -   `implementation_request.md` remains unchanged.
    -   The `DONE` commit is indeed the last one.

---

## 3. Workflow Integration

1.  **Pipeline** emits `StartCoding(context)`.
2.  **AgentHandler** receives event:
    -   Builds RISEN prompt using context (request ID, metadata).
    -   Spawns `gemini-cli` in the `workspace_path`.
3.  **Agent** performs work, commits, and finally creates the `DONE` commit.
4.  **AgentHandler** detects `DONE` commit.
5.  **AgentHandler** emits `WorkCompleted`.
6.  **Pipeline** proceeds to cleanup or push.
