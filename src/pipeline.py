import shutil
import subprocess
import re
from pathlib import Path
from typing import Dict, Any
from bus import EventBus
from events import (
    TaskDetected, RequestWorkspace, WorkspaceReady,
    RequestGitClone, GitReady, RequestBranch, BranchReady,
    RequestCommit, StartCoding, WorkCompleted, RequestPush
)
from utils.parser import extract_metadata

class Pipeline:
    def __init__(self, bus: EventBus, base_workdir: Path, push_on_finish: bool = False):
        self.bus = bus
        self.base_workdir = base_workdir
        self.push_on_finish = push_on_finish
        self._current_task: Dict[str, Any] = {}

        # Wiring
        self.bus.subscribe(TaskDetected, self.on_task_detected)
        self.bus.subscribe(WorkspaceReady, self.on_workspace_ready)
        self.bus.subscribe(GitReady, self.on_git_ready)
        self.bus.subscribe(BranchReady, self.on_branch_ready)
        self.bus.subscribe(WorkCompleted, self.on_work_completed)

    def on_task_detected(self, event: TaskDetected):
        print(f"Task detected: {event.path}")
        metadata = extract_metadata(event.path)
        self._current_task = {
            'metadata': metadata,
            'source_path': event.path
        }
        
        repo_url = metadata['repo']
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        
        self.bus.emit(RequestWorkspace(
            request_id=metadata['id'],
            recipient=metadata['recipient'],
            repo_name=repo_name,
            base_workdir=self.base_workdir
        ))

    def on_workspace_ready(self, event: WorkspaceReady):
        self._current_task['workspace_path'] = event.path
        metadata = self._current_task['metadata']
        
        self.bus.emit(RequestGitClone(
            repo_url=metadata['repo'],
            workspace_path=event.path
        ))

    def on_git_ready(self, event: GitReady):
        metadata = self._current_task['metadata']
        
        self.bus.emit(RequestBranch(
            workspace_path=event.workspace_path,
            base_commit=metadata['base_commit'],
            feature_branch=metadata['feature_branch']
        ))

    def on_branch_ready(self, event: BranchReady):
        workspace_path = event.workspace_path
        metadata = self._current_task['metadata']
        source_path = self._current_task['source_path']
        
        # Request Injection & Initial Commit (moved from main.py logic)
        repo_name = metadata['repo'].split("/")[-1].replace(".git", "")
        request_id = metadata['id']
        target_request_path = workspace_path / source_path.name
        
        numeric_match = re.search(r'(\d+)$', request_id)
        numeric_id = numeric_match.group(1).zfill(4) if numeric_match else "0000"
        commit_msg = f"[implementation request]: {repo_name}-{numeric_id}"

        # Check if bootstrap commit exists
        log_check = subprocess.run(
            ['git', 'log', '--grep', f"\\[implementation request\\]: {repo_name}-{numeric_id}"], 
            cwd=workspace_path, capture_output=True, text=True
        )
        
        if commit_msg not in log_check.stdout:
            shutil.copy2(source_path, target_request_path)
            self.bus.emit(RequestCommit(
                workspace_path=workspace_path,
                request_file=target_request_path,
                commit_message=commit_msg
            ))
            self._current_task['bootstrap_skipped'] = False
        else:
            print(f"Bootstrap commit '{commit_msg}' already exists. Skipping injection.")
            self._current_task['bootstrap_skipped'] = True
        
        # Now trigger the agent
        self.bus.emit(StartCoding(context=metadata))

    def on_work_completed(self, event: WorkCompleted):
        print("Work completed by agent.")
        if self.push_on_finish:
            if not self._current_task.get('bootstrap_skipped', False):
                metadata = self._current_task['metadata']
                self.bus.emit(RequestPush(
                    workspace_path=self._current_task['workspace_path'],
                    feature_branch=metadata['feature_branch']
                ))
            else:
                print("Skipping push because bootstrap commit was already present.")
        
        print(f"Pipeline finished for task {self._current_task['metadata']['id']}")
