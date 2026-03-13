@echo off
title AiPet Launcher
echo Starting AiPet backend...
start "AiPet Backend" cmd /k "cd /d %~dp0..\backend && python main.py"
timeout /t 3 /nobreak > nul
echo Starting AiPet frontend...
start "AiPet Frontend" cmd /k "cd /d %~dp0..\frontend && npm run electron:dev"
echo AiPet started! Hotkey: Ctrl+Shift+A
pause
