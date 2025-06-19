#!/usr/bin/env python3
"""
Test script for MCP Streamable HTTP transport
"""

import asyncio
import aiohttp
import json
import sys

async def test_mcp_http():
    """Test the MCP server's HTTP transport."""
    base_url = "http://localhost:3000"
    
    # Test endpoints
    endpoints = [
        "/mcp/v1/messages",  # Standard MCP endpoint
        "/health",           # Health check (if available)
        "/",                 # Root endpoint
    ]
    
    print("🧪 Testing MCP Streamable HTTP Transport")
    print(f"🌐 Base URL: {base_url}")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Health check / Root endpoint
        print("\n1️⃣  Testing root endpoint...")
        try:
            async with session.get(f"{base_url}/") as response:
                print(f"   Status: {response.status}")
                text = await response.text()
                print(f"   Response: {text[:100]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 2: List available tools
        print("\n2️⃣  Testing tools/list...")
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 1
            }
            
            async with session.post(
                f"{base_url}/mcp/v1/messages",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"   Status: {response.status}")
                result = await response.json()
                print(f"   Found {len(result.get('result', {}).get('tools', []))} tools")
                
                # Show first few tool names
                tools = result.get('result', {}).get('tools', [])
                if tools:
                    print(f"   Sample tools: {[t['name'] for t in tools[:5]]}")
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 3: Call a simple discovery tool
        print("\n3️⃣  Testing simple tool call...")
        try:
            payload = {
                "jsonrpc": "2.0", 
                "method": "tools/call",
                "params": {
                    "name": "list_nodes",
                    "arguments": {}
                },
                "id": 2
            }
            
            async with session.post(
                f"{base_url}/mcp/v1/messages",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"   Status: {response.status}")
                result = await response.json()
                
                if 'result' in result:
                    content = result['result']['content'][0]['text']
                    print(f"   Response: {content[:200]}...")
                else:
                    print(f"   Error: {result.get('error', 'Unknown error')}")
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    print("Make sure to start the MCP server first:")
    print("python main.py --mode http --port 3000")
    print("\nPress Enter to continue with tests...")
    input()
    
    asyncio.run(test_mcp_http())