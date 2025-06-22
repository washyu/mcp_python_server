# MCP HTTP Transport Session Management Guide

## Problem Summary

When implementing MCP HTTP transport, you may encounter a "Bad Request: Missing session ID" error even when providing session ID headers. This is due to a combination of MCP specification requirements and FastMCP implementation issues.

## Root Causes

### 1. FastMCP Session ID Bug
- **Issue**: FastMCP 2.5.1 has a known bug where it doesn't properly recognize session ID headers
- **Symptom**: Server responds with "Missing session ID" even when `X-Session-ID` header is provided
- **Affected**: FastMCP versions 2.5.1 and potentially others

### 2. Incorrect Header Name
- **Issue**: Using `X-Session-ID` instead of the MCP specification standard
- **Correct Header**: `Mcp-Session-Id` (per MCP specification)
- **Common Mistake**: Using `X-Session-ID` (non-standard)

### 3. Session Initialization Sequence
- **Issue**: Calling tools without proper MCP initialization
- **Requirement**: Must call `initialize` method before any other operations
- **Flow**: `initialize` → `tools/list` → `tools/call`

## Solutions

### Solution 1: Use Stateless HTTP Mode (Recommended)

Modify your FastMCP server initialization to use stateless mode:

```python
from mcp.server import FastMCP

# Use stateless mode to bypass session ID issues
mcp = FastMCP("your-server-name", stateless_http=True)
```

**Benefits:**
- Eliminates session ID requirements
- Each request is independent
- Works around FastMCP session bug
- Simpler client implementation

### Solution 2: Correct Header Implementation

If you need session-based mode, use the correct header:

```python
headers = {
    "Content-Type": "application/json",
    "Mcp-Session-Id": your_session_id  # Correct header name
}
```

### Solution 3: Proper Initialization Sequence

Always initialize before using tools:

```python
# 1. Initialize first (no session ID)
init_payload = {
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {"tools": {"listChanged": False}},
        "clientInfo": {"name": "your-client", "version": "1.0.0"}
    },
    "id": 1
}

# 2. Extract session ID from response headers (if needed)
# Look for "Mcp-Session-Id" header in response

# 3. Use session ID in subsequent requests
headers = {"Mcp-Session-Id": session_id}
```

## MCP HTTP Transport Specification

### Session Management Rules

1. **Optional Sessions**: Session IDs are optional but if used, must be consistent
2. **Header Name**: Use `Mcp-Session-Id` header (not `X-Session-ID`)
3. **Initialization**: Session ID may be returned during `initialize` call
4. **Persistence**: Include session ID in all subsequent requests
5. **Termination**: Server may terminate sessions, client must handle 404 responses

### Request Flow

```
Client                          Server
  |                               |
  |-- initialize (no session) --->|
  |<-- response + session ID -----|
  |                               |
  |-- tools/list (+ session) ---->|
  |<-- tools list ----------------|
  |                               |
  |-- tools/call (+ session) ---->|
  |<-- tool result ---------------|
```

### HTTP Status Codes

- **200**: Success
- **400**: Bad Request (missing session ID, invalid JSON-RPC)
- **404**: Session not found or endpoint not found
- **405**: Method not allowed

## Implementation Examples

### Correct Client Implementation

```python
import aiohttp
import json

class MCPHTTPClient:
    def __init__(self, base_url, stateless=True):
        self.base_url = base_url
        self.stateless = stateless
        self.session_id = None
        
    def _get_headers(self, include_session=True):
        headers = {"Content-Type": "application/json"}
        if include_session and self.session_id and not self.stateless:
            headers["Mcp-Session-Id"] = self.session_id
        return headers
    
    async def initialize(self):
        payload = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {"listChanged": False}},
                "clientInfo": {"name": "client", "version": "1.0.0"}
            },
            "id": 1
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/mcp/v1/messages",
                json=payload,
                headers=self._get_headers(include_session=False)
            ) as response:
                if response.status == 200:
                    # Check for session ID in response headers
                    if "Mcp-Session-Id" in response.headers:
                        self.session_id = response.headers["Mcp-Session-Id"]
                    return await response.json()
                else:
                    raise Exception(f"HTTP {response.status}: {await response.text()}")
```

### Correct Server Implementation

```python
from mcp.server import FastMCP

# Option 1: Stateless mode (recommended)
mcp = FastMCP("server-name", stateless_http=True)

# Option 2: Session-based mode (if needed)
mcp = FastMCP("server-name")  # Default behavior

# Register tools normally
@mcp.tool()
async def my_tool():
    return "Hello from MCP server!"

# Run server
if __name__ == "__main__":
    mcp.run()
```

## Testing Your Implementation

### Test Script Usage

1. **Start your MCP server**:
   ```bash
   python main.py --mode http --port 3000
   ```

2. **Run the test client**:
   ```bash
   python test_mcp_http_correct.py
   ```

3. **Check for common issues**:
   - ✅ Stateless mode bypasses session issues
   - ✅ Correct header names are used
   - ✅ Proper initialization sequence
   - ✅ Error handling for different scenarios

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| "Missing session ID" | FastMCP session bug | Use `stateless_http=True` |
| "404 Not Found" | Wrong endpoint | Try `/mcp/v1/messages` |
| "Method not found" | No initialization | Call `initialize` first |
| Connection refused | Server not running | Start MCP server |

## Best Practices

### For Server Developers

1. **Use Stateless Mode**: Eliminates session complexity
2. **Proper Error Handling**: Return meaningful error messages
3. **Support Multiple Endpoints**: `/mcp/v1/messages`, `/mcp`, `/messages`
4. **Validation**: Validate JSON-RPC format and required fields

### For Client Developers

1. **Initialize First**: Always call `initialize` before tools
2. **Handle Retries**: Try different endpoints if one fails
3. **Session Handling**: Check for session IDs in response headers
4. **Error Recovery**: Handle 404s by reinitializing
5. **Timeouts**: Use reasonable request timeouts

### For Production Deployments

1. **Load Balancing**: Consider session affinity if using sessions
2. **Monitoring**: Track session creation/termination rates
3. **Security**: Validate session IDs, implement rate limiting
4. **Scaling**: Prefer stateless mode for horizontal scaling

## Files in This Repository

- `test_mcp_http_correct.py` - Correct MCP HTTP client implementation
- `test_fastmcp_session_fix.py` - FastMCP-specific session testing
- `src/server/mcp_server.py` - Updated server with stateless mode
- `MCP_HTTP_SESSION_GUIDE.md` - This guide

## References

- [MCP Specification - Transports](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)
- [FastMCP Session ID Issue #808](https://github.com/modelcontextprotocol/python-sdk/issues/808)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)

---

**Summary**: The "Missing session ID" error is typically caused by FastMCP's session handling bug. The recommended solution is to use `stateless_http=True` when initializing FastMCP servers, which bypasses session requirements entirely and provides better scalability.