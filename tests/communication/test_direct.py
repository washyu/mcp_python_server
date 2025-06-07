#!/usr/bin/env python3
"""
Direct test of MCP server functionality.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from server.server import app
from mcp.server.stdio import stdio_server


async def test_direct():
    """Test MCP server directly without subprocess."""
    print("Testing MCP server directly...")
    
    # Import the actual handler functions
    from server.server import list_tools, call_tool
    
    # Get available tools
    tools = await list_tools()
    print(f"Available tools: {[t.name for t in tools]}")
    
    # Call hello_world tool
    result = await call_tool("hello_world", {})
    print(f"Tool result: {[content.text for content in result]}")
    
    print("\nDirect test passed!")


if __name__ == "__main__":
    asyncio.run(test_direct())