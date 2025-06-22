#\!/bin/bash

SESSION_ID="test-session-$(date +%s)"
echo "Testing MCP initialization with session: $SESSION_ID"

# Step 1: Initialize
echo "Step 1: Initializing session..."
curl -s -X POST "http://localhost:5173/mcp/v1/messages" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Session-ID: $SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-03-26",
      "capabilities": {
        "experimental": {},
        "tools": {"listChanged": false}
      },
      "clientInfo": {
        "name": "test-client",
        "version": "1.0.0"
      }
    },
    "id": 1
  }' | jq .

# Step 2: List tools
echo -e "\nStep 2: Listing tools..."
curl -s -X POST "http://localhost:5173/mcp/v1/messages" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Session-ID: $SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 2
  }' | jq '.result.tools | length'
