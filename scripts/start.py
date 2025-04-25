#!/usr/bin/env python3
"""
This script runs the Procrai application, which consists of a FastAPI backend
and a Streamlit frontend.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

def run_backend():
    """
    Run the FastAPI backend server
    """
    os.environ["PYTHONPATH"] = f"{os.environ.get('PYTHONPATH', '')}:{Path(__file__).parent}/src"
    backend_cmd = ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    return subprocess.Popen(backend_cmd)

def run_frontend():
    """
    Run the Streamlit frontend
    """
    os.environ["PYTHONPATH"] = f"{os.environ.get('PYTHONPATH', '')}:{Path(__file__).parent}/src"
    frontend_cmd = ["streamlit", "run", "src/ui/main.py"]
    return subprocess.Popen(frontend_cmd)

def main():
    """
    Run both the frontend and backend
    """
    print("Starting Procrai application...")

    # Start backend
    backend_process = run_backend()
    print("Backend server started on http://localhost:8000")

    # Give backend time to start
    time.sleep(2)

    # Start frontend
    frontend_process = run_frontend()
    print("Frontend started on http://localhost:8501")

    try:
        # Keep the script running
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        backend_process.terminate()
        frontend_process.terminate()
        sys.exit(0)

if __name__ == "__main__":
    main()
