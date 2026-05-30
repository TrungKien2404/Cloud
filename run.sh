#!/bin/bash
# Stock Prediction System Unified Bash Runner for Linux/macOS
# Created by Antigravity DeepMind Team

echo "==================================================="
echo " 📈 STOCK PREDICTION SYSTEM - UNIX QUICKSTART"
echo "==================================================="

# Check python
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python is not installed or not in PATH!"
    exit 1
fi

echo "Starting system using active environment with $PYTHON_CMD..."
$PYTHON_CMD run_all.py
