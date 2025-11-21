#!/bin/bash
# Simple script to start the backend server with the correct Python environment
cd "$(dirname "$0")"
./venv/bin/python3 run_server.py
