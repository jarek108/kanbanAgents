@echo off
setlocal EnableDelayedExpansion
echo Starting Vibe Kanban Web UI on 127.0.0.1:61154 from local fork...

:: 1. Check for Node requirements
where pnpm >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo pnpm not found. Installing pnpm globally...
    call npm install -g pnpm
)
where cross-env >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo cross-env not found. Installing cross-env globally...
    call npm install -g cross-env
)

:: 2. Check for Rust requirements (cargo)
where cargo >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo.
    echo =====================================================
    echo ERROR: Rust is not installed.
    echo Vibe Kanban requires Rust to compile the local backend.
    echo.
    echo Please install Rust manually:
    echo 1. Go to https://rustup.rs/
    echo 2. Download and run rustup-init.exe
    echo 3. Restart your terminal/computer and run this script again.
    echo =====================================================
    echo.
    pause
    exit /b 1
)

:: 3. Check for cargo-watch
cargo watch --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo cargo-watch not found. Installing via cargo...
    cargo install cargo-watch
)

set FORK_DIR=%~dp0..\vibe-kanban

if not exist "%FORK_DIR%" (
    echo Cloning fork...
    git clone https://github.com/jarek108/vibe-kanban.git "%FORK_DIR%"
)

cd /d "%FORK_DIR%"

echo Ensuring kanbanAgents branch...
git fetch origin kanbanAgents
git checkout kanbanAgents

echo Installing dependencies...
call pnpm install

echo Building npx-cli...
cd npx-cli
call npm run build
cd ..

echo Starting dev server...
set HOST=127.0.0.1
set PORT=61154
call pnpm run dev:win
endlocal
