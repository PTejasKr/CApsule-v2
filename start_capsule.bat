@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo Starting Capsule backend...
echo.

where docker >nul 2>nul
if errorlevel 1 (
    echo Docker was not found on PATH.
    echo Install Docker Desktop and start it before running this script.
    pause
    exit /b 1
)

docker compose up -d --build
if errorlevel 1 (
    echo.
    echo Failed to start Capsule. Check Docker Desktop and the compose configuration.
    pause
    exit /b 1
)

echo.
echo Capsule backend started successfully.
echo.
echo Local test links:
echo   - API root: http://localhost:8000/
echo   - Dashboard: http://localhost:8000/dashboard
echo   - Swagger docs: http://localhost:8000/docs
echo   - Nginx endpoint: http://localhost/
echo.
echo Persistent storage:
echo   - PostgreSQL data is stored in Docker volume: pgdata
echo   - App data is mounted from: .\data
echo   - BRD files are mounted from: .\brd
echo.
echo Opening the dashboard and API root in your browser...
start "" http://localhost:8000/
start "" http://localhost:8000/dashboard

echo Press any key to close this window.
pause >nul
