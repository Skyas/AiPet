@echo off
title AiPet Voice Module Install
echo Installing voice module deps (optional)...
cd /d %~dp0..\backend
pip install -r requirements_voice.txt
echo Done! Enable voice module in AiPet settings.
pause
