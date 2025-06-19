#!/usr/bin/env python3
"""
Quick test of MCP HTTP transport without user interaction
"""

import asyncio
import aiohttp
import json
import uuid

async def quick_test():
    """Quick test of MCP HTTP transport."""
    base_url = "http://localhost:3000"
    
    print("🧪 Quick MCP HTTP Test")
    print(f"🌐 Testing: {base_url}")
    
    async with aiohttp.ClientSession() as session:
        try:
            # Test tools/list
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/list", 
                "params": {},
                "id": 1
            }
            
            # Try multiple possible endpoints
            endpoints = ["/mcp/v1/messages", "/v1/messages", "/messages", "/mcp"]
            success = False
            
            for endpoint in endpoints:
                try:
                    async with session.post(
                        f"{base_url}{endpoint}",
                        json=payload,
                        headers={
                            "Content-Type": "application/json",
                            "Accept": "application/json, text/event-stream",
                            "X-Session-ID": str(uuid.uuid4())
                        },
                        timeout=aiohttp.ClientTimeout(total=5)
                        ) as response:
                        if response.status == 200:
                            result = await response.json()
                            tools = result.get('result', {}).get('tools', [])
                            print(f"✅ Server responded on {endpoint}: {len(tools)} tools available")
                            print(f"   Sample tools: {[t['name'] for t in tools[:3]]}")
                            success = True
                            break
                        elif response.status == 404:
                            continue  # Try next endpoint
                        else:
                            print(f"❌ HTTP {response.status} on {endpoint}: {await response.text()}")
                            continue
                except Exception as e:
                    print(f"   Error on {endpoint}: {e}")
                    continue
            
            if success:
                return True
            else:
                print("❌ No working endpoints found")
                return False
                    
        except asyncio.TimeoutError:
            print("❌ Connection timeout - server not running?")
            return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False

if __name__ == "__main__":
    success = asyncio.run(quick_test())
    if not success:
        print("\n💡 To start the server:")
        print("   python main.py --mode http --port 3000")