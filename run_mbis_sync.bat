@echo off
REM =======================================================
REM MBIS (MIMO Business Intelligence System) Automation Script
REM =======================================================

echo ======================================================= >> logs\sync.log
echo [MBIS SYNC START] %DATE% %TIME% >> logs\sync.log
echo ======================================================= >> logs\sync.log

cd /d "c:\Users\HP\PycharmProjects\PythonProject"

REM Run main.py using virtual environment Python interpreter
.\.venv\Scripts\python.exe main.py >> logs\sync.log 2>&1

echo ======================================================= >> logs\sync.log
echo [MBIS SYNC FINISHED] %DATE% %TIME% >> logs\sync.log
echo ======================================================= >> logs\sync.log
echo. >> logs\sync.log
