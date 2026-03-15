#!/usr/bin/env python3
"""
Headless Gemini CLI Invoker

This script acts as a standalone utility to execute the Gemini CLI as a 
non-interactive, background worker. It is designed to take a specific prompt 
and execute it within a target workspace directory.

Usage:
    python scripts/headless_gemini.py -w /path/to/project -p "Implement feature X"

Options:
    -w, --workspace  The directory where the agent should run.
    -p, --prompt     The instruction or prompt for the agent.
    -m, --model      (Optional) The model to use (default: gemini-3-flash-preview).
    --no-confirm     (Optional) Disable the auto-confirm (-y) flag.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

def invoke_agent(workspace_path: Path, prompt: str, model: str = "gemini-3-flash-preview", auto_confirm: bool = True):
    """
    Invokes the Gemini CLI synchronously as a headless worker.
    """
    if not workspace_path.exists() or not workspace_path.is_dir():
        print(f"Error: Workspace path does not exist or is not a directory: {workspace_path}", file=sys.stderr)
        return False

    # Build the command
    cmd = ["gemini"]
    
    if auto_confirm:
        cmd.append("-y")
        
    if model:
        cmd.extend(["--model", model])
        
    cmd.extend(["-p", prompt.strip()])

    print(f"--- Launching Headless Agent ---", flush=True)
    print(f"Workspace: {workspace_path}")
    print(f"Model:     {model}")
    print(f"Prompt:    {prompt[:100]}{'...' if len(prompt) > 100 else ''}\n", flush=True)

    try:
        # Run synchronously, allowing stdout/stderr to stream to the console
        result = subprocess.run(cmd, cwd=str(workspace_path))
        
        if result.returncode == 0:
            print(f"\n--- Agent Finished Successfully ---")
            return True
        else:
            print(f"\n--- Agent Failed (Exit Code: {result.returncode}) ---", file=sys.stderr)
            return False

    except FileNotFoundError:
        print("\nError: 'gemini' command not found. Ensure the Gemini CLI is installed and in your PATH.", file=sys.stderr)
        # Fallback check for Windows npm roaming path
        alt_path = Path(os.environ.get("APPDATA", "")) / "npm" / "gemini.cmd"
        if alt_path.exists():
            print(f"Hint: Found gemini at {alt_path}. Try adding it to PATH.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"\n--- Agent Execution Error ---", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Run Gemini CLI as a headless worker.")
    parser.add_argument("-w", "--workspace", required=True, type=str, help="Target workspace directory.")
    parser.add_argument("-p", "--prompt", required=True, type=str, help="The instruction for the agent.")
    parser.add_argument("-m", "--model", type=str, default="gemini-3-flash-preview", help="Model to use (default: gemini-3-flash-preview).")
    parser.add_argument("--no-confirm", action="store_true", help="Disable the auto-confirm (-y) flag.")

    args = parser.parse_args()
    
    workspace = Path(args.workspace).resolve()
    success = invoke_agent(workspace, args.prompt, args.model, not args.no_confirm)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
