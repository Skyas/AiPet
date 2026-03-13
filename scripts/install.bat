@echo off
title AiPet Install
echo Installing Python backend deps...
cd /d %~dp0..\backend
pip install -r requirements.txt
echo.
echo Installing Node.js frontend deps...
cd /d %~dp0..\frontend
npm install
echo.
echo Done! Run start.bat to launch AiPet.
pause
