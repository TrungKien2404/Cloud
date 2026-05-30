@echo off
REM Stock Prediction System Unified Batch Runner for Windows
REM Created by Antigravity DeepMind Team

echo ===================================================
echo  📈 STOCK PREDICTION SYSTEM - WINDOWS QUICKSTART
echo ===================================================

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.11 or higher and try again.
    pause
    exit /b 1
)

echo Starting system using active environment...
python run_all.py

if %errorlevel% neq 0 (
    echo.
    echo [INFO] System terminated with status %errorlevel%
)
