import subprocess
import os
import shutil
from pathlib import Path
from bus import EventBus
from events import StartCoding, WorkCompleted

CODING_PROMPT_TEMPLATE = """
# MANDATORY TASK
Implement the feature described in @implementation_request.md.

# PHASE 1: CODING ONLY
- YOUR GOAL: Functional implementation that passes requirements.
- INPUT: @implementation_request.md
- **RESTRICTION:** DO NOT read or modify 'implementation_report.md'. It is for later.
- **GIT MANDATE:** Use `git add`, `git commit`, and `git push` for EVERY change.

# COMPLETION SIGNAL
When code is verified and pushed, you MUST:
1. `git commit --allow-empty -m "DONE_CODING"`
2. `git push`
3. STOP immediately.
"""

REPORT_PROMPT_TEMPLATE = """
# MANDATORY TASK
Refine @implementation_report.md based on the code you just wrote.

# PHASE 2: REPORTING ONLY
- YOUR GOAL: Documentation and finalization.
- **RESTRICTION:** DO NOT modify any code files (like .py files). Only modify the report.
- **GIT MANDATE:**
   - `git add implementation_report.md`
   - `git commit -m "docs: finalize implementation report"`
   - `git push`

# COMPLETION SIGNAL
When report is pushed, you MUST:
1. `git commit --allow-empty -m "DONE_REPORTING"`
2. `git push`
3. STOP immediately.
"""

class AgentHandler:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.bus.subscribe(StartCoding, self.on_start)

    def _get_last_commit_message(self, workspace_path: Path) -> str:
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--pretty=%B'],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""

    def _is_workspace_dirty(self, workspace_path: Path) -> bool:
        """Checks if there are uncommitted changes (tracked or untracked)."""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                check=True
            )
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            return True

    def _invoke_agent(self, workspace_path: Path, prompt: str):
        """Invokes the Gemini agent with a given prompt."""
        gemini_path = r"C:\\Users\\admin\\AppData\\Roaming\\npm\\gemini.cmd"
        if not os.path.exists(gemini_path):
            gemini_path = "gemini"
            
        cmd = [gemini_path, "-y", "--model", "gemini-3-flash-preview", "-p", prompt.strip()]
        
        try:
            subprocess.run(cmd, cwd=workspace_path, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"AgentHandler: Agent execution failed: {e}")
            return False

    def _fail_safe_commit_and_push(self, workspace_path: Path, message: str, signal: str):
        """Final fail-safe to ensure work is committed and pushed."""
        print(f"AgentHandler: Running fail-safe for signal {signal}...")
        try:
            # 1. Stage and commit actual work
            subprocess.run(['git', 'add', '.'], cwd=workspace_path, check=True)
            status_result = subprocess.run(['git', 'status', '--porcelain'], cwd=workspace_path, capture_output=True, text=True, check=True)
            if status_result.stdout.strip():
                subprocess.run(['git', 'commit', '-m', message], cwd=workspace_path, check=True)
            
            # 2. Add the specific phase signal
            if self._get_last_commit_message(workspace_path) != signal:
                subprocess.run(['git', 'commit', '--allow-empty', '-m', signal], cwd=workspace_path, check=True)
            
            # 3. Push
            print(f"AgentHandler: Pushing fail-safe {signal} to remote...")
            try:
                subprocess.run(['git', 'push'], cwd=workspace_path, check=True)
            except subprocess.CalledProcessError:
                subprocess.run(['git', 'push', 'origin', 'HEAD'], cwd=workspace_path, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"AgentHandler: Fail-safe failed: {e}")
            return False

    def on_start(self, event: StartCoding):
        workspace_path = event.workspace_path
        
        # --- PHASE 1: CODING ---
        print(f"AgentHandler: [PHASE 1] Coding task {event.context.get('id')}...")
        self._invoke_agent(workspace_path, CODING_PROMPT_TEMPLATE)
        
        # Second Chance Safety for Phase 1
        if self._get_last_commit_message(workspace_path) != "DONE_CODING" or self._is_workspace_dirty(workspace_path):
            print("AgentHandler: Phase 1 incomplete or dirty. Prompting agent for final check...")
            
            try:
                task_def = (workspace_path / "implementation_request.md").read_text(encoding='utf-8')
            except:
                task_def = "Task definition unavailable."

            final_check_prompt = f"""
# FINAL CHECK
You have stopped working, but the 'DONE_CODING' signal is missing or there are uncommitted changes.
Are you finished with the following task?

---
{task_def}
---

If YES:
1. Commit all your implementation work now.
2. Push your changes.
3. Commit an EMPTY message 'DONE_CODING'.
4. Push it.

If NO:
1. Finish the task.
2. Perform the steps above.
"""
            self._invoke_agent(workspace_path, final_check_prompt)

        # Final Verify Phase 1: Manual wrap if still failing
        if self._get_last_commit_message(workspace_path) != "DONE_CODING" or self._is_workspace_dirty(workspace_path):
            print("AgentHandler: Phase 1 STILL incomplete. Wrapping up manually...")
            self._fail_safe_commit_and_push(workspace_path, "auto: wrap coding work", "DONE_CODING")

        # --- PHASE 2: REPORTING ---
        print(f"AgentHandler: [PHASE 2] Reporting task {event.context.get('id')}...")
        self._invoke_agent(workspace_path, REPORT_PROMPT_TEMPLATE)

        # Verify Phase 2: Last commit must be DONE_REPORTING AND workspace must be clean
        if self._get_last_commit_message(workspace_path) != "DONE_REPORTING" or self._is_workspace_dirty(workspace_path):
            print("AgentHandler: Phase 2 incomplete or dirty. Wrapping up...")
            self._fail_safe_commit_and_push(workspace_path, "auto: wrap reporting work", "DONE_REPORTING")

        # Final check
        if self._get_last_commit_message(workspace_path) == "DONE_REPORTING":
            print("AgentHandler: Pipeline finished successfully.")
            self.bus.emit(WorkCompleted(diff=None))
        else:
            print("AgentHandler: Pipeline failed final signal check.")
            self.bus.emit(WorkCompleted(diff="FAILED_PHASE_2"))
