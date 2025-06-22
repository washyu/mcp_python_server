#!/usr/bin/env python3
"""
Correct MCP HTTP Client Implementation

This demonstrates the proper way to implement an MCP HTTP client based on:
1. MCP specification requirements
2. FastMCP stateless mode fix
3. Proper header handling and session management
"""

import asyncio
import aiohttp
import json
import sys
from typing import Optional, Dict, Any, List

class MCPHTTPClient:
    """A correct implementation of MCP HTTP transport client."""
    
    def __init__(self, base_url: str, stateless: bool = True):
        self.base_url = base_url.rstrip('/')
        self.stateless = stateless
        self.session_id: Optional[str] = None
        self.initialized = False
        self.server_info: Optional[Dict[str, Any]] = None
        self.client_session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.client_session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client_session:
            await self.client_session.close()
    
    def _get_headers(self, include_session_id: bool = True) -> Dict[str, str]:
        """Get HTTP headers for MCP requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Add session ID if we have one and server requires it
        if include_session_id and self.session_id and not self.stateless:
            # Use the correct MCP specification header name
            headers["Mcp-Session-Id"] = self.session_id
            
        return headers
    
    async def _make_request(
        self, 
        method: str, 
        params: Dict[str, Any] = None, 
        request_id: int = 1
    ) -> Dict[str, Any]:
        """Make a JSON-RPC request to the MCP server."""
        if not self.client_session:
            raise RuntimeError("Client session not initialized. Use async context manager.")
            
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": request_id
        }
        
        # For initialization, don't include session ID
        include_session = method != "initialize"
        headers = self._get_headers(include_session_id=include_session)
        
        # Try the standard MCP endpoint first, then fallbacks
        endpoints = ["/mcp/v1/messages", "/mcp", "/messages"]
        
        for endpoint in endpoints:
            url = f"{self.base_url}{endpoint}"
            
            try:
                async with self.client_session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # Extract session ID from initialize response if present
                        if method == "initialize" and not self.stateless:
                            # Check response headers for session ID
                            session_headers = ["Mcp-Session-Id", "mcp-session-id"]
                            for header_name in session_headers:
                                if header_name in response.headers:
                                    self.session_id = response.headers[header_name]
                                    break
                        
                        return result
                        
                    elif response.status == 404:
                        # Try next endpoint
                        continue
                    else:
                        # Log error but try next endpoint
                        error_text = await response.text()
                        print(f"Warning: {endpoint} returned {response.status}: {error_text}")
                        continue
                        
            except Exception as e:
                print(f"Warning: Error on {endpoint}: {e}")
                continue
        
        raise Exception(f"All endpoints failed for method: {method}")
    
    async def initialize(self) -> bool:
        """Initialize the MCP connection."""
        if self.initialized:
            return True
            
        print("🔗 Initializing MCP connection...")
        
        params = {
            "protocolVersion": "2025-03-26",
            "capabilities": {
                "experimental": {},
                "tools": {"listChanged": False}
            },
            "clientInfo": {
                "name": "mcp-http-client",
                "version": "1.0.0"
            }
        }
        
        try:
            result = await self._make_request("initialize", params)
            
            if "result" in result:
                self.server_info = result["result"]
                self.initialized = True
                
                server_info = self.server_info.get("serverInfo", {})
                print(f"✅ Connected to: {server_info.get('name', 'Unknown')}")
                print(f"   Version: {server_info.get('version', 'Unknown')}")
                print(f"   Protocol: {self.server_info.get('protocolVersion', 'Unknown')}")
                
                if self.session_id:
                    print(f"   Session ID: {self.session_id}")
                elif self.stateless:
                    print("   Mode: Stateless (no session ID required)")
                
                return True
            else:
                error = result.get("error", {})
                print(f"❌ Initialization failed: {error.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    async def list_tools(self) -> Optional[List[Dict[str, Any]]]:
        """List available tools."""
        if not self.initialized:
            if not await self.initialize():
                return None
        
        try:
            result = await self._make_request("tools/list", {})
            
            if "result" in result:
                tools = result["result"].get("tools", [])
                return tools
            else:
                error = result.get("error", {})
                print(f"❌ Failed to list tools: {error.get('message', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"❌ Error listing tools: {e}")
            return None
    
    async def call_tool(self, name: str, arguments: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Call a tool."""
        if not self.initialized:
            if not await self.initialize():
                return None
        
        try:
            params = {
                "name": name,
                "arguments": arguments or {}
            }
            
            result = await self._make_request("tools/call", params)
            
            if "result" in result:
                return result["result"]
            else:
                error = result.get("error", {})
                print(f"❌ Tool call failed: {error.get('message', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"❌ Error calling tool: {e}")
            return None


async def demo_correct_mcp_http_client():
    """Demonstrate the correct MCP HTTP client usage."""
    base_url = "http://localhost:3000"
    
    print("🧪 MCP HTTP Client - Correct Implementation Demo")
    print(f"🌐 Server: {base_url}")
    print("=" * 50)
    
    # Use stateless mode (recommended for FastMCP)
    async with MCPHTTPClient(base_url, stateless=True) as client:
        
        # Step 1: Initialize connection
        if not await client.initialize():
            print("\n💡 Troubleshooting tips:")
            print("   1. Make sure MCP server is running:")
            print("      python main.py --mode http --port 3000")
            print("   2. Server should use stateless_http=True")
            print("   3. Check server logs for errors")
            return
        
        # Step 2: List available tools
        print("\n🔧 Listing available tools...")
        tools = await client.list_tools()
        
        if tools:
            print(f"✅ Found {len(tools)} tools:")
            for i, tool in enumerate(tools[:10]):  # Show first 10
                print(f"   {i+1:2d}. {tool.get('name', 'Unknown')}")
                desc = tool.get('description', '')
                if desc:
                    print(f"       {desc[:60]}{'...' if len(desc) > 60 else ''}")
            
            if len(tools) > 10:
                print(f"   ... and {len(tools) - 10} more tools")
        else:
            print("❌ No tools available")
            return
        
        # Step 3: Call a simple tool
        print("\n⚡ Testing tool calls...")
        
        # Try to find a simple discovery tool
        test_tools = [
            ("list_nodes", "List Proxmox nodes"),
            ("hello_world", "Simple hello world test"),
            ("get_server_status", "Get server status"),
            ("discover_infrastructure", "Discover infrastructure")
        ]
        
        tool_called = False
        for tool_name, description in test_tools:
            if any(t.get("name") == tool_name for t in tools):
                print(f"🎯 Calling: {tool_name} ({description})")
                result = await client.call_tool(tool_name)
                
                if result:
                    print("✅ Tool call successful!")
                    
                    # Display result content
                    content = result.get("content", [])
                    if content and isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and "text" in item:
                                text = item["text"]
                                # Show first few lines
                                lines = text.split('\n')[:3]
                                for line in lines:
                                    print(f"   {line}")
                                if len(text.split('\n')) > 3:
                                    print("   ...")
                    
                    tool_called = True
                    break
                else:
                    print(f"❌ Tool call failed: {tool_name}")
        
        if not tool_called:
            # Try the first available tool
            if tools:
                first_tool = tools[0]
                tool_name = first_tool.get("name", "unknown")
                print(f"🎯 Calling first available tool: {tool_name}")
                result = await client.call_tool(tool_name)
                
                if result:
                    print("✅ Tool call successful!")
                else:
                    print("❌ Tool call failed")
        
        print("\n" + "=" * 50)
        print("🎯 Demo Complete!")
        print(f"   Connection: {'Stateless' if client.stateless else 'Session-based'}")
        print(f"   Tools Available: {len(tools) if tools else 0}")
        print(f"   Session ID: {client.session_id or 'N/A'}")


async def test_session_vs_stateless():
    """Compare session-based vs stateless modes."""
    base_url = "http://localhost:3000"
    
    print("\n" + "=" * 50)
    print("🔍 Comparing Session vs Stateless Modes")
    print("=" * 50)
    
    # Test stateless mode (recommended)
    print("\n1️⃣  Testing Stateless Mode (Recommended)")
    async with MCPHTTPClient(base_url, stateless=True) as client:
        success = await client.initialize()
        print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
        if success:
            tools = await client.list_tools()
            print(f"   Tools: {len(tools) if tools else 0}")
    
    # Test session-based mode (may fail with FastMCP bug)
    print("\n2️⃣  Testing Session-based Mode (May fail with FastMCP)")
    async with MCPHTTPClient(base_url, stateless=False) as client:
        success = await client.initialize()
        print(f"   Result: {'✅ Success' if success else '❌ Failed (expected with FastMCP bug)'}")
        if success:
            tools = await client.list_tools()
            print(f"   Tools: {len(tools) if tools else 0}")
            print(f"   Session ID: {client.session_id}")


if __name__ == "__main__":
    print("🚀 MCP HTTP Transport - Correct Implementation")
    print("📚 This demonstrates the proper way to implement MCP over HTTP")
    print("\n⚠️  Prerequisites:")
    print("   1. Start MCP server: python main.py --mode http --port 3000")
    print("   2. Server should use FastMCP with stateless_http=True")
    print("\nPress Enter to continue...")
    input()
    
    # Run the main demo
    asyncio.run(demo_correct_mcp_http_client())
    
    # Compare modes
    asyncio.run(test_session_vs_stateless())