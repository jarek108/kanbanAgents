import subprocess
from pathlib import Path
from bus import EventBus
from events import (
    RequestGitClone, GitReady, 
    RequestBranch, BranchReady,
    RequestPush, PushCompleted,
    RequestCommit
)

class GitHandler:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.bus.subscribe(RequestGitClone, self.on_clone)
        self.bus.subscribe(RequestBranch, self.on_branch)
        self.bus.subscribe(RequestPush, self.on_push)
        self.bus.subscribe(RequestCommit, self.on_commit)

    def _run_git(self, args, cwd: Path):
        result = subprocess.run(['git'] + args, cwd=cwd, capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def _is_git_repo(self, repo_path: Path) -> bool:
        return (repo_path / '.git').exists()

    def _branch_exists(self, repo_path: Path, branch_name: str) -> bool:
        result = subprocess.run(['git', 'branch', '--list', branch_name], cwd=repo_path, capture_output=True, text=True)
        return branch_name in result.stdout

    def on_clone(self, event: RequestGitClone):
        if self._is_git_repo(event.workspace_path):
            print(f"Repository already exists in {event.workspace_path}, skipping clone.")
        else:
            print(f"Cloning {event.repo_url}...")
            subprocess.run(['git', 'clone', event.repo_url, '.'], cwd=event.workspace_path, check=True)
        self.bus.emit(GitReady(workspace_path=event.workspace_path))

    def on_branch(self, event: RequestBranch):
        repo_path = event.workspace_path
        feature_branch = event.feature_branch
        base_commit = event.base_commit

        if self._branch_exists(repo_path, feature_branch):
            print(f"Branch {feature_branch} already exists. Checking out and pulling...")
            self._run_git(['checkout', feature_branch], cwd=repo_path)
            try:
                self._run_git(['pull', 'origin', feature_branch], cwd=repo_path)
            except subprocess.CalledProcessError:
                print(f"Pull failed for {feature_branch}. Branch may not exist on remote yet.")
        else:
            print(f"Aligning state to {base_commit} and creating branch {feature_branch}...")
            self._run_git(['checkout', '-b', feature_branch, base_commit], cwd=repo_path)
        
        self.bus.emit(BranchReady(workspace_path=repo_path))

    def on_commit(self, event: RequestCommit):
        print(f"Creating bootstrap commit: {event.commit_message}")
        self._run_git(['add', event.request_file.name], cwd=event.workspace_path)
        self._run_git(['commit', '-m', event.commit_message], cwd=event.workspace_path)

    def on_push(self, event: RequestPush):
        print(f"Pushing branch {event.feature_branch} to origin...")
        self._run_git(['push', 'origin', event.feature_branch], cwd=event.workspace_path)
        self.bus.emit(PushCompleted(workspace_path=event.workspace_path))
