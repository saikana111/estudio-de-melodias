@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" src\dashboard.py
) else if exist "..\.tools\python\python.exe" (
  "..\.tools\python\python.exe" src\dashboard.py
) else (
  python src\dashboard.py
)
if errorlevel 1 pause
