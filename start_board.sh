#!/bin/bash
set -e
echo "Starting Vibe Kanban Web UI on 127.0.0.1:61154 from local fork..."

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORK_DIR="$DIR/../vibe-kanban"

if [ ! -d "$FORK_DIR" ]; then
    echo "Cloning fork..."
    git clone https://github.com/jarek108/vibe-kanban.git "$FORK_DIR"
fi

cd "$FORK_DIR"
echo "Ensuring kanbanAgents branch..."
git fetch origin kanbanAgents
git checkout kanbanAgents

echo "Installing dependencies..."
pnpm install

echo "Building npx-cli..."
cd npx-cli
npm run build
cd ..

echo "Starting dev server..."
HOST=127.0.0.1 PORT=61154 pnpm run dev
