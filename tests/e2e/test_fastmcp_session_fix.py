#!/usr/bin/env python3
"""
Test FastMCP HTTP transport session management with proper fixes.

Based on research:
1. FastMCP 2.5.1 has issues with session ID recognition
2. The MCP spec uses "Mcp-Session-Id" header (not "X-Session-ID")
3. FastMCP can be run in stateless mode to avoid session issues
4. Proper initialization sequence is required before tool calls
"""

import asyncio
import aiohttp
import json
import sys
import uuid
from typing import Optional, Dict, Any

class FastMCPClient:
    """A client that properly handles FastMCP HTTP transport sessions."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session_id: Optional[str] = None
        self.initialized = False
        self.server_info: Optional[Dict[str, Any]] = None
        
    async def _make_request(
        self, 
        method: str, 
        params: Dict[str, Any] = None, 
        use_session_id: bool = True,
        request_id: int = None
    ) -> Dict[str, Any]:
        """Make a JSON-RPC request to the FastMCP server."""
        if params is None:
            params = {}
            
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id or 1
        }
        
        # Set up headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Add session ID header if we have one and it's needed
        if use_session_id and self.session_id:
            # Try both header names - the spec says Mcp-Session-Id but FastMCP might expect X-Session-ID
            headers["Mcp-Session-Id"] = self.session_id
            headers["X-Session-ID"] = self.session_id  # Fallback for FastMCP bug
        
        print(f"🔗 Making request: {method}")
        print(f"   Headers: {headers}")
        print(f"   Payload: {json.dumps(payload, indent=2)}")
        
        async with aiohttp.ClientSession() as session:
            # Try multiple possible endpoints
            endpoints = ["/mcp/v1/messages", "/mcp", "/messages", "/"]
            
            for endpoint in endpoints:
                try:
                    full_url = f"{self.base_url}{endpoint}"
                    print(f"   Trying endpoint: {full_url}")
                    
                    async with session.post(
                        full_url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        response_text = await response.text()
                        print(f"   Status: {response.status}")
                        print(f"   Response: {response_text[:200]}...")
                        
                        if response.status == 200:
                            try:
                                result = json.loads(response_text)
                                
                                # Check for session ID in response headers
                                if not self.session_id and method == "initialize":
                                    session_id_headers = ["Mcp-Session-Id", "X-Session-ID", "mcp-session-id"]
                                    for header_name in session_id_headers:
                                        if header_name in response.headers:
                                            self.session_id = response.headers[header_name]
                                            print(f"   📋 Got session ID from {header_name}: {self.session_id}")
                                            break
                                
                                return result
                            except json.JSONDecodeError as e:
                                print(f"   ❌ JSON decode error: {e}")
                                continue
                        elif response.status == 400 and "Missing session ID" in response_text:
                            print(f"   ⚠️  FastMCP session ID issue detected")
                            # This is the known FastMCP bug - try stateless mode suggestion
                            continue
                        elif response.status == 404:
                            print(f"   ⚠️  Endpoint not found, trying next...")
                            continue
                        else:
                            print(f"   ❌ HTTP {response.status}: {response_text}")
                            continue
                            
                except Exception as e:
                    print(f"   ❌ Error on {endpoint}: {e}")
                    continue
            
            raise Exception(f"No working endpoints found for {method}")
    
    async def initialize(self) -> bool:
        """Initialize the MCP session."""
        if self.initialized:
            return True
            
        print("\n🚀 Initializing MCP Session...")
        
        init_params = {
            "protocolVersion": "2025-03-26",
            "capabilities": {
                "experimental": {},
                "tools": {"listChanged": False}
            },
            "clientInfo": {
                "name": "fastmcp-test-client",
                "version": "1.0.0"
            }
        }
        
        try:
            result = await self._make_request("initialize", init_params, use_session_id=False, request_id=1)
            
            if "result" in result:
                self.server_info = result["result"]
                self.initialized = True
                
                server_info = self.server_info.get("serverInfo", {})
                print(f"   ✅ Connected to: {server_info.get('name', 'Unknown')} v{server_info.get('version', 'Unknown')}")
                print(f"   Protocol: {self.server_info.get('protocolVersion', 'Unknown')}")
                
                # Check server capabilities
                capabilities = self.server_info.get("capabilities", {})
                print(f"   Capabilities: {list(capabilities.keys())}")
                
                return True
            else:
                error = result.get("error", {})
                print(f"   ❌ Initialization failed: {error.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"   ❌ Initialization error: {e}")
            return False
    
    async def list_tools(self) -> Optional[list]:
        """List available tools."""
        if not self.initialized:
            if not await self.initialize():
                return None
        
        print("\n🔧 Listing Tools...")
        
        try:
            result = await self._make_request("tools/list", {}, request_id=2)
            
            if "result" in result:
                tools = result["result"].get("tools", [])
                print(f"   ✅ Found {len(tools)} tools")
                for i, tool in enumerate(tools[:5]):  # Show first 5
                    print(f"   {i+1}. {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
                if len(tools) > 5:
                    print(f"   ... and {len(tools) - 5} more")
                return tools
            else:
                error = result.get("error", {})
                print(f"   ❌ Failed to list tools: {error.get('message', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"   ❌ Error listing tools: {e}")
            return None
    
    async def call_tool(self, name: str, arguments: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Call a specific tool."""
        if not self.initialized:
            if not await self.initialize():
                return None
        
        if arguments is None:
            arguments = {}
            
        print(f"\n⚡ Calling Tool: {name}")
        
        try:
            params = {
                "name": name,
                "arguments": arguments
            }
            
            result = await self._make_request("tools/call", params, request_id=3)
            
            if "result" in result:
                tool_result = result["result"]
                print(f"   ✅ Tool executed successfully")
                
                # Extract and display content
                content = tool_result.get("content", [])
                if content and isinstance(content, list) and len(content) > 0:
                    first_content = content[0]
                    if isinstance(first_content, dict) and "text" in first_content:
                        text = first_content["text"]
                        print(f"   Response: {text[:200]}{'...' if len(text) > 200 else ''}")
                
                return tool_result
            else:
                error = result.get("error", {})
                print(f"   ❌ Tool call failed: {error.get('message', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"   ❌ Error calling tool: {e}")
            return None


async def test_fastmcp_session_management():
    """Test FastMCP HTTP transport with proper session management."""
    base_url = "http://localhost:3000"
    
    print("🧪 Testing FastMCP HTTP Transport Session Management")
    print(f"🌐 Server: {base_url}")
    print("=" * 60)
    
    client = FastMCPClient(base_url)
    
    # Test 1: Initialize session
    success = await client.initialize()
    if not success:
        print("\n❌ Session initialization failed - check if server is running in stateless mode")
        print("💡 Try starting server with: python main.py --mode http --port 3000")
        print("💡 Or modify FastMCP to use stateless_http=True")
        return False
    
    # Test 2: List tools
    tools = await client.list_tools()
    if not tools:
        print("\n❌ Failed to list tools")
        return False
    
    # Test 3: Call a simple tool
    if tools:
        # Try to find a simple discovery tool
        simple_tools = [
            "list_nodes",
            "hello_world", 
            "get_server_status",
            "list_vms"
        ]
        
        tool_to_call = None
        for simple_tool in simple_tools:
            if any(tool.get("name") == simple_tool for tool in tools):
                tool_to_call = simple_tool
                break
        
        if not tool_to_call and tools:
            # Just use the first available tool
            tool_to_call = tools[0].get("name")
        
        if tool_to_call:
            result = await client.call_tool(tool_to_call)
            if result:
                print(f"\n✅ Successfully called tool: {tool_to_call}")
            else:
                print(f"\n❌ Failed to call tool: {tool_to_call}")
        else:
            print("\n⚠️  No suitable tools found to test")
    
    print("\n" + "=" * 60)
    print("🎯 Test Summary:")
    print(f"   Session ID: {client.session_id or 'None (stateless)'}")
    print(f"   Initialized: {client.initialized}")
    print(f"   Tools Available: {len(tools) if tools else 0}")
    
    return True


async def test_stateless_mode():
    """Test the stateless mode workaround for FastMCP session issues."""
    print("\n" + "=" * 60)
    print("🔄 Testing Stateless Mode Workaround")
    print("=" * 60)
    
    print("💡 The recommended fix for FastMCP session issues:")
    print("   1. Modify your FastMCP server initialization:")
    print("      mcp = FastMCP('server-name', stateless_http=True)")
    print("   2. This bypasses session ID requirements")
    print("   3. Each request is independent (no session state)")
    print("\n🔧 Example server code:")
    print("""
from mcp.server import FastMCP

# Initialize with stateless HTTP mode
mcp = FastMCP("universal-homelab-mcp", stateless_http=True)

# Register your tools normally
@mcp.tool()
async def my_tool():
    return "Hello from stateless server!"

# Run the server
if __name__ == "__main__":
    mcp.run()
    """)


if __name__ == "__main__":
    print("🚀 FastMCP Session Management Test")
    print("📋 This script tests proper session handling for FastMCP HTTP transport")
    print("\n⚠️  Make sure to start your MCP server first:")
    print("   python main.py --mode http --port 3000")
    print("\nPress Enter to continue...")
    input()
    
    success = asyncio.run(test_fastmcp_session_management())
    
    if not success:
        asyncio.run(test_stateless_mode())