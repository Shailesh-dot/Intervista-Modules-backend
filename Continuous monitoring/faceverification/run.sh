#!/bin/bash
# Helper script to ensure the correct virtual environment is used

# Activate the virtual environment
source myenv/bin/activate

# Pass all arguments to main.py
python3 main.py "$@"
