import subprocess
from pathlib import Path

def run_git(args, cwd: Path):
    """Utility to run git commands in a specific directory."""
    result = subprocess.run(['git'] + args, cwd=cwd, capture_output=True, text=True, check=True)
    return result.stdout.strip()

def is_git_repo(repo_path: Path) -> bool:
    """Checks if the directory is already a git repository."""
    return (repo_path / '.git').exists()

def clone_repo(repo_url: str, dest_path: Path):
    """Clones a repository if it doesn't already exist."""
    if is_git_repo(dest_path):
        print(f"Repository already exists in {dest_path}, skipping clone.")
        return
    print(f"Cloning {repo_url}...")
    subprocess.run(['git', 'clone', repo_url, '.'], cwd=dest_path, check=True)

def branch_exists(repo_path: Path, branch_name: str) -> bool:
    """Checks if a branch exists locally."""
    result = subprocess.run(['git', 'branch', '--list', branch_name], cwd=repo_path, capture_output=True, text=True)
    return branch_name in result.stdout

def setup_branch(repo_path: Path, base_commit: str, feature_branch: str):
    """Resets to base commit or switches to/pulls existing branch."""
    if branch_exists(repo_path, feature_branch):
        print(f"Branch {feature_branch} already exists. Checking out and pulling...")
        run_git(['checkout', feature_branch], cwd=repo_path)
        try:
            run_git(['pull', 'origin', feature_branch], cwd=repo_path)
        except subprocess.CalledProcessError:
            print(f"Pull failed for {feature_branch}. Branch may not exist on remote yet.")
    else:
        print(f"Aligning state to {base_commit} and creating branch {feature_branch}...")
        run_git(['checkout', '-b', feature_branch, base_commit], cwd=repo_path)

def commit_request(repo_path: Path, request_file: Path, commit_message: str):
    """Adds the request file and creates the bootstrap commit."""
    print(f"Creating bootstrap commit: {commit_message}")
    run_git(['add', request_file.name], cwd=repo_path)
    run_git(['commit', '-m', commit_message], cwd=repo_path)

def push_branch(repo_path: Path, branch_name: str):
    """Pushes the local branch to the remote origin."""
    print(f"Pushing branch {branch_name} to origin...")
    run_git(['push', 'origin', branch_name], cwd=repo_path)
