@echo off
title AiPet Dev Mode
start "Backend" cmd /k "cd /d %~dp0..\backend && uvicorn main:socket_app --host 0.0.0.0 --port 8000 --reload"
timeout /t 2 /nobreak > nul
start "Frontend" cmd /k "cd /d %~dp0..\frontend && npm run dev"
echo Dev servers running:
echo   Backend:  http://localhost:8000/docs
echo   Frontend: http://localhost:5173
pause
