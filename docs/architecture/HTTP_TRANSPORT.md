# MCP Streamable HTTP Transport Guide

## Overview

Your MCP server now supports **Streamable HTTP transport**, which is the new standard for MCP communication introduced in the 2025-03-26 specification.

## Available Transport Modes

```bash
# Interactive chat (default)
python main.py

# Stdio for Claude Desktop  
python main.py --mode stdio

# WebSocket for real-time apps
python main.py --mode websocket --port 8765

# HTTP for REST API clients (NEW)
python main.py --mode http --port 3000

# SSE for event streaming (NEW)
python main.py --mode sse --port 3000
```

## HTTP Transport Details

### Starting the Server
```bash
python main.py --mode http --host localhost --port 3000
```

### Protocol Requirements
The Streamable HTTP transport uses:
- **Session Management**: Each client needs a session ID
- **Content Negotiation**: Must accept both JSON and event-stream
- **JSON-RPC 2.0**: Standard MCP protocol over HTTP

### Required Headers
```http
Content-Type: application/json
Accept: application/json, text/event-stream
X-Session-ID: <session-id>  # Required for session management
```

### Endpoints
- **Primary**: `/mcp/v1/messages` - Main MCP communication
- **Alternative**: `/mcp` - Simplified endpoint

## Testing the HTTP Transport

### Method 1: Use Test Scripts
```bash
# Interactive test (asks for input)
python test_http_transport.py

# Quick automated test
python test_quick_http.py
```

### Method 2: Direct curl Commands
```bash
# Create session first (if required)
SESSION_ID=$(uuidgen)

# List tools
curl -X POST http://localhost:3000/mcp/v1/messages \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Session-ID: $SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 1
  }'

# Call a tool
curl -X POST http://localhost:3000/mcp/v1/messages \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Session-ID: $SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "list_nodes",
      "arguments": {}
    },
    "id": 2
  }'
```

## Benefits of HTTP Transport

1. **Universal Compatibility** - Works with any HTTP client
2. **Firewall Friendly** - Uses standard HTTP ports (80/443)
3. **Load Balancer Ready** - Can deploy behind reverse proxies
4. **Authentication Ready** - Easy to add API keys, OAuth tokens
5. **Streaming Support** - Handles long operations gracefully
6. **Stateless Operation** - Better for serverless deployment

## Integration Examples

### Web Applications
```javascript
// JavaScript/TypeScript example
const response = await fetch('http://localhost:3000/mcp/v1/messages', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json, text/event-stream',
    'X-Session-ID': crypto.randomUUID()
  },
  body: JSON.stringify({
    jsonrpc: '2.0',
    method: 'tools/list',
    params: {},
    id: 1
  })
});

const result = await response.json();
console.log('Available tools:', result.result.tools);
```

### Python Clients
```python
import aiohttp
import uuid

async def call_mcp_tool(tool_name: str, args: dict = {}):
    session_id = str(uuid.uuid4())
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            'http://localhost:3000/mcp/v1/messages',
            json={
                'jsonrpc': '2.0',
                'method': 'tools/call',
                'params': {'name': tool_name, 'arguments': args},
                'id': 1
            },
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/event-stream',
                'X-Session-ID': session_id
            }
        ) as response:
            return await response.json()
```

### CI/CD Integration
```yaml
# GitHub Actions example
- name: Deploy via MCP
  run: |
    curl -X POST http://mcp-server:3000/mcp/v1/messages \
      -H "Content-Type: application/json" \
      -H "Accept: application/json, text/event-stream" \
      -H "X-Session-ID: $GITHUB_RUN_ID" \
      -d '{
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
          "name": "create_vm",
          "arguments": {
            "name": "production-web-${{ github.sha }}",
            "cores": 4,
            "memory_gb": 8
          }
        },
        "id": 1
      }'
```

## Error Handling

Common errors and solutions:

### Missing Session ID
```json
{
  "error": {
    "code": -32600,
    "message": "Bad Request: Missing session ID"
  }
}
```
**Solution**: Add `X-Session-ID` header with a unique identifier

### Not Acceptable
```json
{
  "error": {
    "code": -32600, 
    "message": "Not Acceptable: Client must accept both application/json and text/event-stream"
  }
}
```
**Solution**: Set `Accept: application/json, text/event-stream` header

### Tool Not Found
```json
{
  "error": {
    "code": -32601,
    "message": "Method not found: invalid_tool_name"
  }
}
```
**Solution**: Use `tools/list` to get available tools first

## Production Deployment

For production deployments, consider:

1. **Reverse Proxy**: Use nginx/Apache for SSL termination
2. **Authentication**: Add API key middleware
3. **Rate Limiting**: Prevent abuse
4. **Monitoring**: Track tool usage and performance
5. **Scaling**: Use multiple server instances behind load balancer

Example nginx configuration:
```nginx
location /mcp/ {
    proxy_pass http://localhost:3000/mcp/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Enable streaming
    proxy_buffering off;
    proxy_cache off;
}
```

## Summary

The HTTP transport makes your MCP server accessible to:
- Web applications and mobile apps
- CI/CD pipelines and automation scripts  
- Third-party integrations and webhooks
- Any system that can make HTTP requests

This significantly expands the reach of your homelab automation beyond just MCP-compatible AI clients!