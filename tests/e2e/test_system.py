#!/usr/bin/env python3
"""
Quick System Test - Verify MCP server and hardware discovery are working
"""

import asyncio
import aiohttp
import sys

async def test_system():
    """Test that the MCP server is working correctly."""
    
    print("🧪 MCP System Health Check")
    print("=" * 40)
    
    # Test 1: Health check
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:3001/health") as response:
                if response.status == 200:
                    print("✅ Chat server health: OK")
                else:
                    print(f"❌ Chat server health: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Chat server unreachable: {e}")
        return False
    
    # Test 2: Tools endpoint
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:3001/api/tools") as response:
                if response.status == 200:
                    data = await response.json()
                    tools = data.get('tools', [])
                    tool_names = [t['name'] for t in tools]
                    
                    if 'discover_remote_system' in tool_names:
                        print("✅ Hardware discovery tools: Available")
                    else:
                        print("❌ Hardware discovery tools: Missing")
                        return False
                        
                    print(f"📊 Total tools available: {len(tools)}")
                else:
                    print(f"❌ Tools endpoint: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Tools endpoint error: {e}")
        return False
    
    # Test 3: Quick chat test
    try:
        test_message = "Hello, can you list your available tools?"
        payload = {
            "messages": [{"role": "user", "content": test_message}],
            "model": "llama3.1:8b",
            "stream": False  # Non-streaming for simple test
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:3001/api/chat", json=payload) as response:
                if response.status == 200:
                    print("✅ Chat endpoint: Responding")
                else:
                    print(f"❌ Chat endpoint: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Chat endpoint error: {e}")
        return False
    
    print("\n🎉 All tests passed! System is ready for use.")
    print("\nTo test hardware discovery:")
    print("1. Open http://localhost:5173 in your browser")
    print("2. Ask: 'What are the hardware specs of system at [your-ip]?'")
    print("3. Verify it uses: EXECUTE_TOOL: discover_remote_system IP: [your-ip]")
    
    return True

if __name__ == "__main__":
    if not asyncio.run(test_system()):
        sys.exit(1)