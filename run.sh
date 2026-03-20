#!/bin/bash
# Convenient runner for the agent pipeline

# Check if we should watch or run a single file
if [[ "$1" == "--watch" ]]; then
    WATCH_DIR="${2:-tasks}"
    echo "Starting Pipeline in Monitor Mode (watching '$WATCH_DIR' directory)..."
    python src/main.py --watch "$WATCH_DIR" --workdir "workspaces" "${@:3}"
elif [[ -f "$1" ]]; then
    echo "Starting Pipeline for request: $1"
    python src/main.py "$1" --workdir "workspaces" "${@:2}"
else
    echo "Usage: ./run.sh [tasks/request.md | --watch [DIR]] [--push]"
    echo ""
    echo "Examples:"
    echo "  ./run.sh tasks/task1.md             # Process single task"
    echo "  ./run.sh --watch                    # Start monitor on 'tasks/'"
    echo "  ./run.sh --watch mocked             # Start monitor on 'mocked/'"
    echo "  ./run.sh tasks/task1.md --push      # Process and push to origin"
fi
