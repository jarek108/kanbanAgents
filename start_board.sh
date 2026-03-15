#!/bin/bash
set -e
echo "Starting Vibe Kanban Web UI on 127.0.0.1:61154 from local fork..."

# --- 1. NODE & PNPM ---
if ! command -v pnpm &> /dev/null; then
    echo "pnpm not found. Installing pnpm globally..."
    npm install -g pnpm
fi
if ! command -v cross-env &> /dev/null; then
    echo "cross-env not found. Installing cross-env globally..."
    npm install -g cross-env
fi

# --- 2. RUST ---
if ! command -v cargo &> /dev/null; then
    echo "cargo not found. Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

# --- 3. C/C++ BUILD TOOLS & LLVM/CLANG (For Bindgen) ---
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux (Debian/Ubuntu based check)
    if command -v apt-get &> /dev/null; then
        if ! dpkg -s build-essential clang libclang-dev &> /dev/null; then
            echo "Missing C/C++ build tools or Clang/LLVM. Installing via apt..."
            sudo apt-get update
            sudo apt-get install -y build-essential clang libclang-dev
        fi
    elif command -v dnf &> /dev/null; then
        # Fedora/RHEL based
        if ! command -v clang &> /dev/null; then
            echo "Missing C/C++ build tools or Clang/LLVM. Installing via dnf..."
            sudo dnf groupinstall -y "Development Tools"
            sudo dnf install -y clang clang-devel
        fi
    elif command -v pacman &> /dev/null; then
        # Arch based
        if ! command -v clang &> /dev/null; then
            echo "Missing C/C++ build tools or Clang/LLVM. Installing via pacman..."
            sudo pacman -S --needed --noconfirm base-devel clang
        fi
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if ! xcode-select -p &> /dev/null; then
        echo "Missing Xcode Command Line Tools. Installing..."
        xcode-select --install
        echo "Please complete the Xcode installation dialog, then run this script again."
        exit 1
    fi
fi

# --- 4. CARGO WATCH ---
if ! cargo watch --version &> /dev/null; then
    echo "cargo-watch not found. Installing via cargo..."
    cargo install cargo-watch
fi

# --- 5. PROJECT SETUP ---
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORK_DIR="$DIR/../vibe-kanban"

if [ ! -d "$FORK_DIR" ]; then
    echo "Cloning vibe-kanban fork - branch main..."
    git clone -b main https://github.com/jarek108/vibe-kanban.git "$FORK_DIR"
fi

cd "$FORK_DIR"
echo "Ensuring main branch..."
git fetch origin main >/dev/null 2>&1 || true
git checkout main >/dev/null 2>&1 || true

echo "Installing pnpm dependencies..."
pnpm install

echo "Building npx-cli..."
cd npx-cli
npm run build
cd ..

# --- 6. START ---
echo
echo "====================================================="
echo "EVERYTHING READY. STARTING LOCAL SERVER..."
echo "====================================================="
export HOST=127.0.0.1
export PORT=61154
export VK_SHARED_API_BASE=https://api.vibekanban.com
pnpm run dev
