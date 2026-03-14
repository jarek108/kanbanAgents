import subprocess
import os
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
            # If directory is not empty, git clone will fail. 
            # We use git init + remote add as a workaround.
            if os.path.exists(event.workspace_path) and os.listdir(event.workspace_path):
                print(f"Directory {event.workspace_path} is not empty. Initializing manually...")
                self._run_git(['init'], cwd=event.workspace_path)
                self._run_git(['remote', 'add', 'origin', event.repo_url], cwd=event.workspace_path)
                self._run_git(['fetch', 'origin'], cwd=event.workspace_path)
            else:
                print(f"Cloning {event.repo_url}...")
                subprocess.run(['git', 'clone', event.repo_url, '.'], cwd=event.workspace_path, check=True)
        self.bus.emit(GitReady(workspace_path=event.workspace_path))

    def on_branch(self, event: RequestBranch):
        repo_path = event.workspace_path
        feature_branch = event.feature_branch
        base_commit = event.base_commit

        # Ensure we are in a clean state
        try:
            self._run_git(['reset', '--hard'], cwd=repo_path)
        except:
            pass

        if self._branch_exists(repo_path, feature_branch):
            print(f"Branch {feature_branch} already exists. Checking out and pulling...")
            self._run_git(['checkout', feature_branch], cwd=repo_path)
            try:
                # Try to pull, but don't fail if it's a new branch or no remote
                self._run_git(['pull', 'origin', feature_branch], cwd=repo_path)
            except subprocess.CalledProcessError:
                print(f"Pull failed for {feature_branch}. Branch may not exist on remote yet or has conflicts.")
        else:
            print(f"Aligning state to {base_commit} and creating branch {feature_branch}...")
            # If base_commit is TBD or empty, default to main/master or current HEAD
            if not base_commit or base_commit == "TBD":
                base_commit = "HEAD"
                
            self._run_git(['checkout', '-b', feature_branch, base_commit], cwd=repo_path)
            
            # Push to origin and set upstream
            print(f"Setting upstream for {feature_branch}...")
            try:
                self._run_git(['push', '-u', 'origin', feature_branch], cwd=repo_path)
            except subprocess.CalledProcessError as e:
                print(f"Initial push failed for {feature_branch}: {e}")
        
        self.bus.emit(BranchReady(workspace_path=repo_path))

    def on_commit(self, event: RequestCommit):
        print(f"Creating bootstrap commit: {event.commit_message}")
        try:
            # Add all injected files (request and report template)
            self._run_git(['add', '.'], cwd=event.workspace_path)
            self._run_git(['commit', '-m', event.commit_message], cwd=event.workspace_path)
            # Crucial: Push the bootstrap commit immediately
            print("Pushing bootstrap commit...")
            self._run_git(['push'], cwd=event.workspace_path)
        except subprocess.CalledProcessError as e:
            print(f"Error during bootstrap commit/push: {e}")

    def on_push(self, event: RequestPush):
        print(f"Pushing branch {event.feature_branch} to origin...")
        self._run_git(['push', 'origin', event.feature_branch], cwd=event.workspace_path)
        self.bus.emit(PushCompleted(workspace_path=event.workspace_path))
