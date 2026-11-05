@echo off
REM Windows Task Scheduler entry point for tools/pc_download.py (see PC_SETUP.md).
cd /d "%~dp0\.."
if exist .venv\Scripts\python.exe (set PY=.venv\Scripts\python.exe) else (set PY=python)
%PY% tools\pc_download.py %* >> pc_download.log 2>&1
