#!/bin/bash

# Real-Time Voice Translator - Linux/macOS Startup Script

echo ""
echo "================================================"
echo " Real-Time Voice Translator"
echo " FastAPI Application Launcher"
echo "================================================"
echo ""

# Check if .venv exists, if not use venv
if [ -d ".venv" ]; then
    echo "Activating virtual environment (.venv)..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "Activating virtual environment (venv)..."
    source venv/bin/activate
else
    echo "ERROR: Virtual environment not found!"
    echo "Please create a virtual environment first:"
    echo "  python -m venv .venv"
    echo "  source .venv/bin/activate"
    exit 1
fi

echo ""
echo "Virtual environment activated successfully!"
echo ""
echo "Starting Real-Time Voice Translator..."
echo "Server will be available at: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the FastAPI server
python main.py
