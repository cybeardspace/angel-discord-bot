#!/usr/bin/env bash
set -e

# Activate the virtual environment created in the Docker build step
source venv/bin/activate

# Execute the main Python application, replacing the current process (PID 1)
exec python angel.py
