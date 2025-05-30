#!/usr/bin/env python3
"""
Debug script to test MCP server communication directly.
"""

import asyncio
import json
import sys


async def test_server_communication():
    """Test sending requests directly to the server via stdin/stdout."""
    
    print("Testing direct server communication...", file=sys.stderr)
    
    # Test 1: Send initialize request
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "0.1.0",
            "capabilities": {}
        },
        "id": 1
    }
    
    print(json.dumps(init_request))
    sys.stdout.flush()
    
    # Test 2: Send tools/list request
    await asyncio.sleep(0.1)
    
    tools_request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 2
    }
    
    print(json.dumps(tools_request))
    sys.stdout.flush()
    
    # Test 3: Call hello_world tool
    await asyncio.sleep(0.1)
    
    call_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "hello_world",
            "arguments": {}
        },
        "id": 3
    }
    
    print(json.dumps(call_request))
    sys.stdout.flush()
    
    # Keep the script running briefly to see responses
    await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(test_server_communication())