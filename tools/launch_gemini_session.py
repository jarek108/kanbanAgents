"""
Gemini CLI Session Launcher for Windows Terminal.

This script automates resuming, cloning, and executing operations in Gemini CLI
sessions within a new Windows Terminal window.

USAGE:
    python tools/launch_gemini_session.py "operation" "session_id" [options]

EXAMPLES:
    python tools/launch_gemini_session.py "Explain this code" latest
      -> Clones latest session, runs "Explain this code" in a new WT using gemini-3-flash-preview, stays open, deletes clone on exit.
    python tools/launch_gemini_session.py "Review PR" 3 --no-preserve --model gemini-2.0-flash-exp
      -> Resumes session index 3 directly (no clone), runs "Review PR" using specific model, stays open.
    python tools/launch_gemini_session.py "Check status" latest --close
      -> Clones latest, runs "Check status", automatically closes terminal and deletes clone when done.
    python tools/launch_gemini_session.py "Start fresh" new
      -> Starts a brand new session, runs "Start fresh", stays open.

PARAMETERS & FLAGS:
    operation (Required)
        The prompt or command string to execute once the Gemini CLI session is ready.
    session_id (Required)
        Identifies the session to resume. Options:
        - "latest": Use the most recently active session.
        - "new": Start a completely fresh session.
        - [index]: The numeric index from `gemini --list-sessions`.
        - [uuid]: The full or partial UUID of a specific session.
    --model, -m (Default: "gemini-3-flash-preview")
        Specifies the AI model to use for the session.
    --preserve, -p (Default: True)
        If true, clones the target session to a temporary file before execution. 
        This ensures the original session history remains unchanged. 
        The cloned session is deleted after the terminal is closed.
    --no-preserve
        Disables cloning. The operation will be appended directly to the 
        original session's history.
    --close, -c (Default: False)
        If set, the Windows Terminal window and the PowerShell process will 
        automatically close once the Gemini operation (and cleanup) is finished.

HOW IT WORKS:
    1. Session Resolution: Fetches available sessions via `gemini --list-sessions` to resolve indices or partial UUIDs.
    2. Cloning: If preservation is enabled, it locates the latest .json session file in ~/.gemini/tmp, 
       copies it with a new UUID, and updates the internal 'sessionId' field.
    3. Scripting: Generates a temporary PowerShell (.ps1) script containing the `gemini` command, 
       cleanup logic (deleting the temp session file), and an optional exit command.
    4. Execution: Launches Windows Terminal (`wt.exe`) pointed at the temporary PowerShell script.
    5. Cleanup: The temporary script deletes itself using `$MyInvocation.MyCommand.Path` after execution.
"""

import os
import sys
import json
import uuid
import subprocess
import argparse
import shutil
from pathlib import Path
from datetime import datetime

def get_sessions():
    """Runs gemini --list-sessions and returns a list of session dictionaries with metadata"""
    try:
        result = subprocess.run(['gemini', '--list-sessions'], capture_output=True, text=True, check=True, shell=True)
        lines = result.stdout.splitlines()
        sessions = []
        
        # We also need to get the file modification times from disk to allow sorting by date
        gemini_tmp = Path.home() / '.gemini' / 'tmp'
        
        for line in lines:
            line = line.strip()
            if not line or not line[0].isdigit():
                continue
            
            if '[' in line and line.endswith(']'):
                parts = line.split('[')
                uuid_str = parts[-1][:-1]
                rest = parts[0].strip()
                index_part = rest.split('.')[0]
                
                # Extract summary and relative time string if present
                # Format: "  1. Summary (2 hours ago) [uuid]"
                summary_part = '.'.join(rest.split('.')[1:]).strip()
                
                # Try to find actual mtime on disk for precise sorting
                mtime = 0
                session_file = find_session_file(uuid_str)
                if session_file:
                    mtime = session_file.stat().st_mtime
                
                sessions.append({
                    'index': int(index_part),
                    'summary': summary_part,
                    'uuid': uuid_str,
                    'mtime': mtime
                })
        return sessions
    except Exception as e:
        print(f"Error listing sessions: {e}")
        return []

def find_session_file(session_uuid):
    """Searches for the latest session file for the given UUID in ~/.gemini/tmp"""
    gemini_tmp = Path.home() / '.gemini' / 'tmp'
    if not gemini_tmp.exists():
        return None
    
    # Search for files containing the UUID prefix (first 8 chars)
    prefix = session_uuid[:8]
    matches = list(gemini_tmp.glob(f'**/chats/session-*-{prefix}.json'))
    
    # Filter for exact sessionId inside JSON if multiple matches
    best_file = None
    latest_time = 0
    
    for match in matches:
        try:
            with open(match, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('sessionId') == session_uuid:
                    mtime = match.stat().st_mtime
                    if mtime > latest_time:
                        latest_time = mtime
                        best_file = match
        except:
            continue
            
    return best_file

def launch_session(operation, session_id, model='gemini-3-flash-preview', preserve=True, close=False):
    is_new = session_id.lower() == 'new'
    target_uuid = None
    dest_file = None

    if is_new:
        preserve = False # Nothing to preserve for a new session
    else:
        sessions = get_sessions()
        if not sessions:
            print("No sessions found for this project.")
            return False
            
        target_session = None
        if session_id == 'latest':
            target_session = sessions[-1]
        else:
            # Try index
            for s in sessions:
                if s['index'] == session_id:
                    target_session = s
                    break
            # Try UUID
            if not target_session:
                for s in sessions:
                    if s['uuid'] == session_id or s['uuid'].startswith(session_id):
                        target_session = s
                        break
                        
        if not target_session:
            print(f"Could not find session matching: {session_id}")
            return False
            
        orig_uuid = target_session['uuid']
        target_uuid = orig_uuid
        
        if preserve:
            source_file = find_session_file(orig_uuid)
            if not source_file:
                print(f"Could not find session file on disk for UUID: {orig_uuid}")
                return False
                
            new_uuid = str(uuid.uuid4())
            # Construct new filename in same directory
            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M")
            new_filename = f"session-{timestamp}-{new_uuid[:8]}.json"
            dest_file = source_file.parent / new_filename
            
            # Load, modify, save
            with open(source_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data['sessionId'] = new_uuid
            data['summary'] = f"TEMP: {data.get('summary', 'Cloned Session')}"
            
            with open(dest_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
            target_uuid = new_uuid
            print(f"Cloned session {orig_uuid} to {target_uuid}")

    # Find absolute path of gemini
    gemini_path = shutil.which("gemini") or "gemini"
    
    # Build the gemini command part
    resume_flag = f"-r {target_uuid}" if target_uuid else ""
    gemini_cmd = f'''& "{gemini_path}" -m {model} {resume_flag} -i "{operation.replace('"', '`"')}"'''

    # Build the powershell script content
    ps_content = f"""
$ErrorActionPreference = 'Stop'
Set-Location -Path "{os.getcwd()}"
try {{
    {gemini_cmd}
}} finally {{
"""
    if preserve:
        # After gemini exits, delete the temp session file
        ps_content += f'    Remove-Item -Path "{dest_file}" -ErrorAction SilentlyContinue\n'
    
    if close:
        ps_content += "    exit\n"
    
    ps_content += "}\n"
    # Self-delete the script
    ps_content += "Remove-Item $MyInvocation.MyCommand.Path\n"

    # Save to a temp file
    temp_id = target_uuid[:8] if target_uuid else str(uuid.uuid4())[:8]
    temp_ps1 = Path.home() / '.gemini' / 'tmp' / f"launch_{temp_id}.ps1"
    with open(temp_ps1, 'w', encoding='utf-8') as f:
        f.write(ps_content)
        
    # Launch Windows Terminal
    shell_args = ["wt", "powershell"]
    if not close:
        shell_args.append("-NoExit")
    
    shell_args.extend(["-ExecutionPolicy", "Bypass", "-File", str(temp_ps1)])
    
    print(f"Launching via temp script {temp_ps1}")
    subprocess.Popen(shell_args)
    return True

def main():
    parser = argparse.ArgumentParser(description='Launch Gemini CLI session in Windows Terminal')
    parser.add_argument('operation', help='The operation string to perform')
    parser.add_argument('session', help='Session ID (index or UUID) or "latest"')
    parser.add_argument('--model', '-m', default='gemini-3-flash-preview', help='Model to use (default: gemini-3-flash-preview)')
    parser.add_argument('--preserve', '-p', action='store_true', default=True, help='Preserve original session (clone it)')
    parser.add_argument('--no-preserve', dest='preserve', action='store_false', help='Do not preserve original session')
    parser.add_argument('--close', '-c', action='store_true', help='Close terminal after execution')
    
    args = parser.parse_args()
    launch_session(args.operation, args.session, args.model, args.preserve, args.close)

if __name__ == "__main__":
    main()
