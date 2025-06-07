#!/usr/bin/env python3
"""
Test script for the MCP server.
This simulates how an AI client would interact with the server.
"""

import json
import asyncio
import sys


async def test_hello_world():
    """Test the hello_world tool by sending MCP protocol messages."""
    
    # This is a simple test that shows what messages would be exchanged
    print("Testing MCP Server Communication...")
    print("\n1. Client -> Server: Initialize")
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "0.1.0",
            "capabilities": {}
        },
        "id": 1
    }
    print(json.dumps(init_request, indent=2))
    
    print("\n2. Client -> Server: List Tools")
    list_tools_request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 2
    }
    print(json.dumps(list_tools_request, indent=2))
    
    print("\n3. Client -> Server: Call hello_world tool")
    call_tool_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "hello_world",
            "arguments": {}
        },
        "id": 3
    }
    print(json.dumps(call_tool_request, indent=2))
    
    print("\nExpected response:")
    expected_response = {
        "jsonrpc": "2.0",
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": "Hello, World!"
                }
            ]
        },
        "id": 3
    }
    print(json.dumps(expected_response, indent=2))


if __name__ == "__main__":
    print("MCP Server Test Script")
    print("=" * 50)
    asyncio.run(test_hello_world())
    print("\n" + "=" * 50)
    print("To actually run the server, use: python main.py")
    print("Or with uv: uv run python main.py")