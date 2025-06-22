#!/usr/bin/env python3
"""
Test MCP HTTP transport initialization sequence.

Based on the WebSocket server implementation, the MCP protocol requires:
1. An 'initialize' method call before any other operations
2. This establishes the session and returns server capabilities
"""

import asyncio
import aiohttp
import json
import sys

async def test_mcp_http_initialization():
    """Test the proper MCP HTTP initialization sequence."""
    base_url = "http://localhost:3000"
    
    print("🧪 Testing MCP HTTP Transport Initialization")
    print(f"🌐 Base URL: {base_url}")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Step 1: Initialize the session
        print("\n1️⃣  Sending initialize request...")
        try:
            init_payload = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {
                        "experimental": {},
                        "tools": {"listChanged": False}
                    },
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                },
                "id": 1
            }
            
            async with session.post(
                f"{base_url}/mcp/v1/messages",
                json=init_payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"   Status: {response.status}")
                result = await response.json()
                print(f"   Response: {json.dumps(result, indent=2)}")
                
                if 'result' in result:
                    server_info = result['result'].get('serverInfo', {})
                    print(f"   ✅ Server: {server_info.get('name')} v{server_info.get('version')}")
                    print(f"   Protocol: {result['result'].get('protocolVersion')}")
                else:
                    print(f"   ❌ Error: {result.get('error', 'Unknown error')}")
                    return
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # Step 2: Now we can list tools
        print("\n2️⃣  Listing tools after initialization...")
        try:
            list_payload = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 2
            }
            
            async with session.post(
                f"{base_url}/mcp/v1/messages",
                json=list_payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"   Status: {response.status}")
                result = await response.json()
                
                if 'result' in result:
                    tools = result['result'].get('tools', [])
                    print(f"   ✅ Found {len(tools)} tools")
                    if tools:
                        print(f"   Sample tools: {[t['name'] for t in tools[:5]]}")
                else:
                    print(f"   ❌ Error: {result.get('error', 'Unknown error')}")
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Step 3: Call a tool
        print("\n3️⃣  Calling a tool after initialization...")
        try:
            call_payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "hello_world",
                    "arguments": {}
                },
                "id": 3
            }
            
            async with session.post(
                f"{base_url}/mcp/v1/messages",
                json=call_payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"   Status: {response.status}")
                result = await response.json()
                
                if 'result' in result:
                    content = result['result']['content'][0]['text']
                    print(f"   ✅ Response: {content}")
                else:
                    print(f"   ❌ Error: {result.get('error', 'Unknown error')}")
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n✅ Initialization sequence complete!")

if __name__ == "__main__":
    print("Make sure to start the MCP server with HTTP transport:")
    print("python main.py --mode http --port 3000")
    print("\nPress Enter to continue...")
    input()
    
    asyncio.run(test_mcp_http_initialization())