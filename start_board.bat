@echo off
setlocal EnableDelayedExpansion
echo Starting Vibe Kanban Web UI on 127.0.0.1:61154...

:: --- 1. NODE & PNPM ---
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

:: --- 2. RUST ---
where cargo >nul 2>nul
if %ERRORLEVEL% neq 0 (
    if not exist "%USERPROFILE%\.cargo\bin\cargo.exe" (
        echo Rust not found. Installing...
        powershell -Command "Invoke-WebRequest -Uri 'https://win.rustup.rs/x86_64' -OutFile '%TEMP%\rustup-init.exe'"
        "%TEMP%\rustup-init.exe" -y --default-toolchain stable --profile default
        del "%TEMP%\rustup-init.exe"
    )
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
)

:: --- 3. MSVC & WINDOWS SDK ---
:: Check for MSVC + Win11 SDK (The core essentials)
set "VS_REQ=Microsoft.VisualStudio.Component.VC.Tools.x86.x64 Microsoft.VisualStudio.Component.Windows11SDK.22621"
for /f "usebackq tokens=*" %%i in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires !VS_REQ! -property installationPath 2^>nul`) do (
    set "VS_PATH=%%i"
)

if not defined VS_PATH (
    echo.
    echo =====================================================
    echo Missing MSVC Build Tools or Windows 11 SDK.
    echo Running Visual Studio Installer...
    echo =====================================================
    
    :: Check if any VS exists to modify
    for /f "usebackq tokens=*" %%i in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -property installationPath 2^>nul`) do (
        set "ANY_VS_PATH=%%i"
    )

    if defined ANY_VS_PATH (
        start /wait "" "%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\setup.exe" modify --installPath "!ANY_VS_PATH!" --quiet --wait --norestart --nocache ^
            --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended ^
            --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 ^
            --add Microsoft.VisualStudio.Component.Windows11SDK.22621
    ) else (
        powershell -Command "Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vs_BuildTools.exe' -OutFile '%TEMP%\vs_BuildTools.exe'"
        start /wait "" "%TEMP%\vs_BuildTools.exe" --quiet --wait --norestart --nocache ^
            --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended ^
            --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 ^
            --add Microsoft.VisualStudio.Component.Windows11SDK.22621
        del "%TEMP%\vs_BuildTools.exe"
    )
    
    :: Re-check after install
    for /f "usebackq tokens=*" %%i in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires !VS_REQ! -property installationPath`) do (
        set "VS_PATH=%%i"
    )
)

if defined VS_PATH (
    if exist "!VS_PATH!\VC\Auxiliary\Build\vcvars64.bat" (
        echo Loading Visual C++ Environment...
        call "!VS_PATH!\VC\Auxiliary\Build\vcvars64.bat" >nul
    )
)

:: --- 4. LLVM / CLANG (For Bindgen) ---
if not exist "C:\Program Files\LLVM\bin\libclang.dll" (
    echo LLVM/Clang not found. Installing via winget...
    winget install -e --id LLVM.LLVM --accept-package-agreements --accept-source-agreements --silent
)
set "LIBCLANG_PATH=C:\Program Files\LLVM\bin"
set "PATH=C:\Program Files\LLVM\bin;%PATH%"
echo LLVM Path set: %LIBCLANG_PATH%

:: --- 5. CARGO WATCH ---
cargo watch --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Installing cargo-watch...
    cargo install cargo-watch
)

:: --- 6. PROJECT SETUP ---
set "FORK_DIR=%~dp0..\vibe-kanban"
if not exist "%FORK_DIR%" (
    echo Cloning vibe-kanban fork - branch kanbanAgents-v2...
    git clone -b kanbanAgents-v2 https://github.com/jarek108/vibe-kanban.git "%FORK_DIR%"
)

cd /d "%FORK_DIR%"
echo Updating repository...
git fetch origin kanbanAgents-v2 >nul 2>nul
git checkout kanbanAgents-v2 >nul 2>nul

echo Installing pnpm dependencies...
call pnpm install

echo Building npx-cli...
cd npx-cli
call npm run build
cd ..

:: --- 7. START ---
echo.
echo =====================================================
echo EVERYTHING READY. STARTING LOCAL SERVER...
echo =====================================================
set HOST=127.0.0.1
set PORT=61154
set VK_SHARED_API_BASE=https://api.vibekanban.com
call pnpm run dev:win
endlocal
