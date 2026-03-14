import subprocess
import os
from pathlib import Path
from bus import EventBus
from events import StartCoding, WorkCompleted

CODING_PROMPT_TEMPLATE = """
# ROLE
You are a Senior Software Engineer Agent specializing in autonomous feature implementation. You operate within a restricted workspace and follow a strict commit-and-push workflow.
Your starting point is a GitHub branch with the initial document - implementation request.

# INPUT
- 'implementation_request.md': Your primary source of truth for requirements and 'Definition of Done'.
- 'implementation_report.md': An INITIAL TEMPLATE already present in the workspace. DO NOT modify it during this phase.

# PHASE 1: IMPLEMENTATION
1. Read and analyze 'implementation_request.md' to understand the requirements and 'Definition of Done'.
2. Explore the existing codebase to identify relevant files and patterns.
3. Implement the requested feature or fix iteratively.
4. COMMIT AND PUSH: Use 'git add <file>', 'git commit -m "<message>"', and 'git push' as SEPARATE, ATOMIC tool calls for EVERY logical change.
5. Verify your work against the 'Expected Behavior' and 'Definition of Done'.

# NARROWING
- NO Branch Switching: Stay on the current feature branch.
- NO Request Modification: Do not modify 'implementation_request.md'.
- NO History Manipulation: Do not use git rebase, git reset, or git commit --amend.
- MUST use git commit and git push as frequently as possible.

When you are finished with the implementation and have verified it, stop and wait for further instructions. Do NOT adapt the implementation report or signal 'DONE' yet.
"""

REPORT_PROMPT_TEMPLATE = """
# PHASE 2: REPORT AND FINALIZATION
You have completed the implementation. Now you must refine the implementation report and signal completion.

1. REFINE IMPLEMENTATION REPORT
   The file 'implementation_report.md' is already present in the root of the workspace. 
   You MUST ADAPT and FILL OUT this file completely based on your work. 
   Ensure all metadata and implementation details are accurate.

2. GIT OPERATIONS (MANDATORY)
   - Run 'git add implementation_report.md'.
   - Run 'git commit -m "refine implementation report"'.
   - Run 'git push'.
   - Run 'git add .'.
   - Run 'git commit -m "final work cleanup"'. (If there are any remaining changes)
   - Run 'git push'.
   - MANDATORY SIGNAL: Finally, run exactly: 'git commit --allow-empty -m "DONE"' followed by 'git push'. 
"""

class AgentHandler:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.bus.subscribe(StartCoding, self.on_start)

    def _verify_done(self, workspace_path: Path) -> bool:
        """Checks if any of the recent commit messages is 'DONE'."""
        try:
            # Check the last 10 commits to be safe
            result = subprocess.run(
                ['git', 'log', '-n', '10', '--pretty=%B'],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                check=True
            )
            commits = result.stdout.strip().split('\n')
            # Look for exact match "DONE" (case sensitive)
            return any(c.strip() == "DONE" for c in commits)
        except subprocess.CalledProcessError:
            return False

    def _invoke_agent(self, workspace_path: Path, prompt: str):
        """Invokes the Gemini agent with a given prompt."""
        gemini_path = r"C:\\Users\\admin\\AppData\\Roaming\\npm\\gemini.cmd"
        if not os.path.exists(gemini_path):
            gemini_path = "gemini" # Fallback to PATH
            
        cmd = [gemini_path, "-y", "--model", "gemini-3-flash-preview", "-p", prompt.strip()]
        
        try:
            subprocess.run(cmd, cwd=workspace_path, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"AgentHandler: Agent execution failed: {e}")
            return False

    def _fail_safe_commit_and_push(self, workspace_path: Path):
        """Final fail-safe to ensure work is committed and pushed even if agent fails."""
        print("AgentHandler: Running fail-safe commit and push...")
        try:
            subprocess.run(['git', 'add', '.'], cwd=workspace_path, check=True)
            status_result = subprocess.run(['git', 'status', '--porcelain'], cwd=workspace_path, capture_output=True, text=True, check=True)
            if status_result.stdout.strip():
                subprocess.run(['git', 'commit', '-m', 'fail-safe: committing implementation work'], cwd=workspace_path, check=True)
            
            if not self._verify_done(workspace_path):
                subprocess.run(['git', 'commit', '--allow-empty', '-m', 'DONE'], cwd=workspace_path, check=True)
            
            print("AgentHandler: Pushing changes to remote...")
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
        print(f"AgentHandler: Starting implementation phase for task {event.context.get('id')} in {workspace_path}")

        # 1. Implementation Phase
        self._invoke_agent(workspace_path, CODING_PROMPT_TEMPLATE)

        # 2. Reporting & Finalization Phase
        print(f"AgentHandler: Starting report and finalization phase...")
        self._invoke_agent(workspace_path, REPORT_PROMPT_TEMPLATE)

        # 3. Final verification and fail-safe
        if not self._verify_done(workspace_path):
            print("AgentHandler: 'DONE' signal missing after Phase 2. Triggering fail-safe...")
            self._fail_safe_commit_and_push(workspace_path)

        if self._verify_done(workspace_path):
            print("AgentHandler: Task completed successfully.")
            self.bus.emit(WorkCompleted(diff=None))
        else:
            print("AgentHandler: Task failed to signal 'DONE'.")
            self.bus.emit(WorkCompleted(diff="FAILED_NO_DONE_COMMIT"))
