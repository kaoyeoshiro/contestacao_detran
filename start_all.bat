@echo off
REM Inicia backend e frontend simultaneamente
set BACKEND_DIR=%~dp0backend
set FRONTEND_DIR=%~dp0frontend\detran

start "backend" cmd /k "cd /d %BACKEND_DIR% && python contestacao.py"
start "frontend" cmd /k "cd /d %FRONTEND_DIR% && npm run dev"

