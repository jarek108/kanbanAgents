# Metadata
ID: IRQ-TEST-001
Recipient: Coder0
Repo: https://github.com/jarek108/testRepo
Base Commit: 800dae7162d3b9d68ae9b109fb7a00209697f515
Feature Branch: feat/0x0001-0-automation

# Summary
Implement a simple standalone HTTP server that responds with "hello from hacathon" to verify the development environment.

# Problem Statement
The workspace lacks a quick verification script to test network binding and basic execution capabilities. We need a minimal, dependency-free server to confirm the agent's ability to create and run executable code.

# Expected Behavior
- A new script (e.g., `simple_server.py`) is created in the repository root.
- The server binds to localhost on a free port (e.g., 8000).
- Visiting the root URL (`/`) returns the exact plain text string: "hello from hacathon".
- The server logs access requests to stdout.

# Goals
2. **Simplicity:** Use only the Python standard library (no `pip install` required).
3. **Correctness:** The output string must match the requirement exactly.

# Non-goals (functional narrowing)
- No deployment scripts or Dockerfiles.
- No advanced routing, middleware, or configuration files.
- No unit tests for this throwaway script.
- Do Not run local server to test it, only focus on coding

# Definition of Done
- `simple_server.py` exists.
- Running the script starts a server.
- A curl request to the server returns "hello from hacathon".
- The original repository code remains untouched.

# Implementation Guidance
Use Python's `http.server` module. Create a custom handler inheriting from `BaseHTTPRequestHandler`. Override `do_GET` to send a 200 OK response with the required byte string.

# Constraints, Assumptions, 'Why nots' (arch narrowing)
- **Constraint:** Do not modify any existing files in the `requests` library.
- **Local Server:** Do not run local server using python command, focus on coding.
- **Assumption:** Python 3 is available in the environment.

# Allowed Architectural Scope
- Creation of new files in the root directory.

# Disallowed Architectural Scope
- Modification of `requests/` directory.
- Modification of `setup.py` or `pyproject.toml`.
- Modification of implementation_request.md file

# References
- [Python http.server documentation](https://docs.python.org/3/library/http.server.html)
