@echo off
cd /d "%~dp0"
if not exist .venv (
  echo Eerste keer: virtuele omgeving aanmaken en pakketten installeren...
  py -3 -m venv .venv || python -m venv .venv
  .venv\Scripts\pip install -r requirements.txt
)
.venv\Scripts\python server.py
pause
