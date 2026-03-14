import argparse
import shutil
import subprocess
from pathlib import Path
from parser import extract_metadata
from workspace import create_workspace
from git_ops import clone_repo, setup_branch, commit_request, push_branch

def main():
    parser = argparse.ArgumentParser(description="Programmatic agent workspace initializer.")
    parser.add_argument("request_file", type=str, help="Path to the implementation_request.md")
    parser.add_argument("--workdir", type=str, default="workspaces", help="Base directory for workspaces")
    parser.add_argument("--push", action="store_true", help="Push the feature branch to origin")
    
    args = parser.parse_args()
    request_file_path = Path(args.request_file).absolute()
    base_workdir = Path(args.workdir).absolute()
    
    if not request_file_path.exists():
        print(f"Error: {request_file_path} not found.")
        return

    print(f"Starting setup from {request_file_path}...")
    
    # 1. Metadata Extraction
    metadata = extract_metadata(request_file_path)
    repo_url = metadata['repo']
    base_commit = metadata['base_commit']
    feature_branch = metadata['feature_branch']
    request_id = metadata['id']
    
    # 2. Workspace Creation
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    workspace_path = create_workspace(base_workdir, repo_name, request_id)
    
    # 3. Repository & State Initialization
    clone_repo(repo_url, workspace_path)
    setup_branch(workspace_path, base_commit, feature_branch)
    
    # 4. Request Injection & Initial Commit
    target_request_path = workspace_path / request_file_path.name
    
    # Extract numeric part of ID (e.g., IRQ-TEST-001 -> 0001)
    import re
    numeric_match = re.search(r'(\d+)$', request_id)
    numeric_id = numeric_match.group(1).zfill(4) if numeric_match else "0000"
    commit_msg = f"[implementation request]: {repo_name}-{numeric_id}"

    # Check if this specific bootstrap commit already exists in current history
    log_check = subprocess.run(['git', 'log', '--grep', f"\\[implementation request\\]: {repo_name}-{numeric_id}"], 
                               cwd=workspace_path, capture_output=True, text=True)
    
    if commit_msg not in log_check.stdout:
        shutil.copy2(request_file_path, target_request_path)
        commit_request(workspace_path, target_request_path, commit_msg)
        
        # 5. Push (Optional)
        if args.push:
            push_branch(workspace_path, feature_branch)
    else:
        print(f"Bootstrap commit '{commit_msg}' already exists. Skipping injection and push.")
    
    print(f"\nWorkspace successfully initialized at: {workspace_path}")

if __name__ == "__main__":
    main()
