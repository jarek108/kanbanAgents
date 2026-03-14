import shutil
from pathlib import Path

def create_workspace(base_path: Path, repo_name: str, feature_id: str) -> Path:
    """Creates a unique workspace directory for the agent or returns existing one."""
    workspace_name = f"{repo_name}_{feature_id}".replace("/", "_")
    workspace_path = base_path / workspace_name
    
    if workspace_path.exists():
        print(f"Using existing workspace: {workspace_path}")
    else:
        workspace_path.mkdir(parents=True, exist_ok=True)
        print(f"Created new workspace: {workspace_path}")
        
    return workspace_path
