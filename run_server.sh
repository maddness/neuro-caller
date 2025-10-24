#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Run Flask server
echo "🚀 Starting Neuro-Caller server..."
python src/app.py
