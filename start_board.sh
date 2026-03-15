#!/bin/bash
set -e
echo "Starting Vibe Kanban Web UI on 127.0.0.1:61154 from local fork..."

# 1. Check for Node requirements
if ! command -v pnpm &> /dev/null; then
    echo "pnpm not found. Installing pnpm globally..."
    npm install -g pnpm
fi
if ! command -v cross-env &> /dev/null; then
    echo "cross-env not found. Installing cross-env globally..."
    npm install -g cross-env
fi

# 2. Check for Rust requirements (cargo)
if ! command -v cargo &> /dev/null; then
    echo "cargo not found. Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

# 3. Check for cargo-watch
if ! cargo watch --version &> /dev/null; then
    echo "cargo-watch not found. Installing via cargo..."
    cargo install cargo-watch
fi

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORK_DIR="$DIR/../vibe-kanban"

if [ ! -d "$FORK_DIR" ]; then
    echo "Cloning fork..."
    git clone https://github.com/jarek108/vibe-kanban.git "$FORK_DIR"
fi

cd "$FORK_DIR"
echo "Ensuring main branch..."
git fetch origin main
git checkout main

echo "Installing dependencies..."
pnpm install

echo "Building npx-cli..."
cd npx-cli
npm run build
cd ..

echo "Starting dev server..."
export HOST=127.0.0.1
export PORT=61154
export VK_SHARED_API_BASE=https://api.vibekanban.com
pnpm run dev
