from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional

@dataclass
class Event:
    pass

# Triggers
@dataclass
class TaskDetected(Event):
    path: Path

# Commands (Pipeline -> Handlers)
@dataclass
class RequestWorkspace(Event):
    request_id: str
    recipient: str
    repo_name: str
    base_workdir: Path
    source_path: Optional[Path] = None
    report_template_path: Optional[Path] = None

@dataclass
class RequestGitClone(Event):
    repo_url: str
    workspace_path: Path

@dataclass
class RequestBranch(Event):
    workspace_path: Path
    base_commit: str
    feature_branch: str

@dataclass
class RequestPush(Event):
    workspace_path: Path
    feature_branch: str

@dataclass
class RequestCommit(Event):
    workspace_path: Path
    request_file: Path
    commit_message: str

@dataclass
class StartCoding(Event):
    workspace_path: Path
    context: Dict[str, Any]

# Signals (Handlers -> Pipeline)
@dataclass
class WorkspaceReady(Event):
    path: Path

@dataclass
class GitReady(Event):
    workspace_path: Path

@dataclass
class BranchReady(Event):
    workspace_path: Path

@dataclass
class PushCompleted(Event):
    workspace_path: Path

@dataclass
class WorkCompleted(Event):
    diff: Optional[str] = None
