#!/usr/bin/env python3
"""
Headless Gemini CLI Invoker

This script acts as a standalone utility and a core engine module to execute 
the Gemini CLI as a non-interactive, background worker. It is designed to take 
a specific prompt and execute it within a target workspace directory, capturing 
output and enforcing timeouts.

Usage:
    python core/headless_gemini.py -w /path/to/project -p "Implement feature X"
"""

import os
import sys
import argparse
import subprocess
import shutil
from pathlib import Path
from typing import Tuple, Optional, Dict

def invoke_agent(
    workspace_path: Path, 
    prompt: str, 
    model: str = "gemini-3-flash-preview", 
    auto_confirm: bool = True,
    timeout: Optional[int] = 900,
    env: Optional[Dict[str, str]] = None
) -> Tuple[bool, str, str]:
    """
    Invokes the Gemini CLI synchronously as a headless worker.
    
    Args:
        workspace_path: Path to the target Git repository/folder.
        prompt: The instruction to pass to the agent.
        model: The model string to use.
        auto_confirm: Whether to pass the '-y' flag to auto-confirm actions.
        timeout: Maximum execution time in seconds (default 15 minutes).
        env: Optional environment variables dictionary to inject.
        
    Returns:
        (success_boolean, stdout_string, stderr_string)
    """
    if not workspace_path.exists() or not workspace_path.is_dir():
        err = f"Error: Workspace path does not exist or is not a directory: {workspace_path}"
        return False, "", err

    # Resolve absolute path to avoid Windows issues
    gemini_path = shutil.which("gemini")
    
    if not gemini_path:
        # Fallback check for Windows npm roaming path
        alt_path = Path(os.environ.get("APPDATA", "")) / "npm" / "gemini.cmd"
        if alt_path.exists():
            gemini_path = str(alt_path)
        else:
            err = "Error: 'gemini' command not found. Ensure the Gemini CLI is installed and in your PATH."
            return False, "", err

    # Build the command
    cmd = [gemini_path]
    if auto_confirm:
        cmd.append("-y")
    if model:
        cmd.extend(["--model", model])
        
    # Ensure string limit safety by passing the prompt cleanly
    cmd.extend(["-p", prompt.strip()])

    # Prepare environment
    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    try:
        # We use shell=True on Windows for .cmd files if needed
        use_shell = os.name == 'nt' and gemini_path.lower().endswith('.cmd')
        
        result = subprocess.run(
            cmd, 
            cwd=str(workspace_path), 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            env=run_env,
            shell=use_shell
        )
        
        if result.returncode == 0:
            return True, result.stdout, result.stderr
        else:
            return False, result.stdout, result.stderr

    except subprocess.TimeoutExpired as e:
        err = f"Agent execution timed out after {timeout} seconds."
        out = e.stdout.decode('utf-8') if isinstance(e.stdout, bytes) else (e.stdout or "")
        err_out = e.stderr.decode('utf-8') if isinstance(e.stderr, bytes) else (e.stderr or "")
        return False, out, f"{err}\n{err_out}"
    except Exception as e:
        return False, "", f"Agent Execution Error: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description="Run Gemini CLI as a headless worker.")
    parser.add_argument("-w", "--workspace", required=True, type=str, help="Target workspace directory.")
    parser.add_argument("-p", "--prompt", required=True, type=str, help="The instruction for the agent.")
    parser.add_argument("-m", "--model", type=str, default="gemini-3-flash-preview", help="Model to use.")
    parser.add_argument("--no-confirm", action="store_true", help="Disable the auto-confirm (-y) flag.")
    parser.add_argument("-t", "--timeout", type=int, default=900, help="Timeout in seconds (default 900).")

    args = parser.parse_args()
    
    workspace = Path(args.workspace).resolve()
    print(f"--- Launching Headless Agent ---", flush=True)
    print(f"Workspace: {workspace}")
    print(f"Model:     {args.model}")
    print(f"Prompt:    {args.prompt[:100]}{'...' if len(args.prompt) > 100 else ''}\n", flush=True)

    success, stdout, stderr = invoke_agent(
        workspace_path=workspace, 
        prompt=args.prompt, 
        model=args.model, 
        auto_confirm=not args.no_confirm,
        timeout=args.timeout
    )
    
    if stdout:
        print("\n--- STDOUT ---\n" + stdout)
    if stderr:
        print("\n--- STDERR ---\n" + stderr, file=sys.stderr)

    if success:
        print(f"\n--- Agent Finished Successfully ---")
        sys.exit(0)
    else:
        print(f"\n--- Agent Failed ---", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
