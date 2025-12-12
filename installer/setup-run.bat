@echo off
echo Setting up Offline Scouting Manager...
echo.

REM Check if uv is installed
uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: uv is not installed!
    echo.
    echo Please install uv first by visiting:
    echo https://docs.astral.sh/uv/getting-started/installation/
    echo.
    echo After installing uv, rerun this script to set up the application.
    pause
    exit /b 1
)

echo uv is installed. Proceeding with setup...
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
uv run main.py --production

if %errorlevel% neq 0 (
    echo Failed to run the application.
    pause
    exit /b 1
)

echo.
echo Installation and startup complete!
pause