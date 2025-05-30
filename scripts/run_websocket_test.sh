#!/bin/bash
# Script to test WebSocket MCP server with agent

echo "Starting MCP WebSocket server in background..."
uv run python main.py --transport websocket &
SERVER_PID=$!

# Give server time to start
sleep 2

echo "Running test agent..."
uv run python test_agent_websocket.py

# Kill server when done
echo "Stopping server..."
kill $SERVER_PID 2>/dev/null