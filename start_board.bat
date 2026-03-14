@echo off
setlocal
echo Starting Vibe Kanban Web UI on 127.0.0.1:61154 from local fork...

where pnpm >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo pnpm not found. Installing pnpm globally...
    call npm install -g pnpm
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
