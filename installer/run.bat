@echo off
echo Installing Offline Scouting Manager...
echo.

REM Check if uv is already installed
uv --version >nul 2>&1
if %errorlevel% equ 0 (
    echo uv is already installed.
    goto :run_app
)

echo Installing uv...
REM Download and install uv
powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
if %errorlevel% neq 0 (
    echo Failed to install uv. Please check your internet connection.
    pause
    exit /b 1
)

REM Add uv to PATH for current session
set PATH=%USERPROFILE%\.cargo\bin;%PATH%

:run_app
echo.
echo Setting up Python environment and dependencies...
cd /d "%~dp0.."

REM Verify we're in the correct directory and main.py exists
if not exist "main.py" (
    echo Error: main.py not found in current directory.
    echo Current directory: %CD%
    pause
    exit /b 1
)

echo Running from directory: %CD%
uv run main.py

if %errorlevel% neq 0 (
    echo Failed to run the application.
    pause
    exit /b 1
)

echo.
echo Installation and startup complete!
pause