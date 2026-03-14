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
    echo Rust is not installed. Installing Rust automatically...
    echo =====================================================
    echo.
    
    :: Download rustup-init.exe
    powershell -Command "Invoke-WebRequest -Uri 'https://win.rustup.rs/x86_64' -OutFile '%TEMP%\rustup-init.exe'"
    
    :: Run the installer silently
    echo Running installer...
    "%TEMP%\rustup-init.exe" -y --default-toolchain stable --profile default
    
    :: Clean up installer
    del "%TEMP%\rustup-init.exe"
    
    :: Manually add cargo to the current session's PATH
    echo Injecting Cargo into current PATH...
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
)

:: 3. Check for MSVC Build Tools (link.exe) which Rust needs on Windows
where cl.exe >nul 2>nul
if %ERRORLEVEL% neq 0 (
    :: Try to find it via vswhere if it's installed but not in PATH
    "%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo.
        echo =====================================================
        echo Microsoft C++ Build Tools not found.
        echo Downloading and installing MSVC Build Tools automatically...
        echo This may take a few minutes and require Administrator privileges.
        echo =====================================================
        echo.
        
        :: Download vs_buildtools
        powershell -Command "Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vs_BuildTools.exe' -OutFile '%TEMP%\vs_BuildTools.exe'"
        
        :: Install silently with necessary components for Rust
        echo Running Visual Studio Installer...
        start /wait "" "%TEMP%\vs_BuildTools.exe" --quiet --wait --norestart --nocache ^
            --add Microsoft.VisualStudio.Workload.VCTools ^
            --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 ^
            --add Microsoft.VisualStudio.Component.Windows11SDK.10.0.22621
            
        :: Clean up installer
        del "%TEMP%\vs_BuildTools.exe"
        
        echo Build Tools installed. 
        echo IMPORTANT: You may need to restart your terminal/computer for PATH changes to take effect.
    )
)

:: 4. Check for cargo-watch
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
