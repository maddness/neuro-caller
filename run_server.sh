#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Run both Flask and WebSocket servers
echo "🚀 Starting Neuro-Caller servers..."
echo "   - Flask server (HTTP): port 3000"
echo "   - WebSocket server (WS): port 3001"
echo ""
python start_servers.py
