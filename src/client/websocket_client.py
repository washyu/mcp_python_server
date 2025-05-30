"""
WebSocket client for MCP server.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
import websockets
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """Represents an available MCP tool."""
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPWebSocketClient:
    """Client for connecting to MCP WebSocket server."""
    
    def __init__(self, uri: str = "ws://localhost:8765"):
        self.uri = uri
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.tools: Dict[str, MCPTool] = {}
        self._request_id = 0
        self.initialized = False
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
    
    async def connect(self):
        """Connect to the MCP server."""
        self.websocket = await websockets.connect(self.uri)
        
        # Initialize the connection
        await self.initialize()
        
        # Get available tools
        await self.refresh_tools()
    
    async def disconnect(self):
        """Disconnect from the server."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
    
    def _next_id(self) -> int:
        """Get next request ID."""
        self._request_id += 1
        return self._request_id
    
    async def _send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a request and wait for response."""
        if not self.websocket:
            raise Exception("Not connected to server")
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self._next_id()
        }
        
        # Send request
        await self.websocket.send(json.dumps(request))
        
        # Wait for response
        response_text = await self.websocket.recv()
        response = json.loads(response_text)
        
        # Check for errors
        if "error" in response:
            raise Exception(f"Server error: {response['error']}")
        
        return response.get("result", {})
    
    async def initialize(self):
        """Initialize the MCP connection."""
        result = await self._send_request("initialize", {
            "protocolVersion": "0.1.0",
            "capabilities": {},
            "clientInfo": {
                "name": "mcp-websocket-client",
                "version": "0.1.0"
            }
        })
        
        self.initialized = True
        logger.info(f"Connected to server: {result.get('serverInfo')}")
        return result
    
    async def refresh_tools(self):
        """Get list of available tools."""
        result = await self._send_request("tools/list")
        
        self.tools.clear()
        for tool_data in result.get("tools", []):
            tool = MCPTool(
                name=tool_data["name"],
                description=tool_data["description"],
                input_schema=tool_data.get("inputSchema", {})
            )
            self.tools[tool.name] = tool
        
        return list(self.tools.values())
    
    async def call_tool(self, name: str, arguments: Dict[str, Any] = None) -> str:
        """Call a tool and return the result."""
        result = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments or {}
        })
        
        # Extract text content
        for content in result.get("content", []):
            if content.get("type") == "text":
                return content["text"]
        
        return str(result)


async def test_websocket_client():
    """Test the WebSocket MCP client."""
    print("Testing WebSocket MCP Client...")
    
    try:
        async with MCPWebSocketClient() as client:
            print(f"Connected to {client.uri}")
            print(f"Initialized: {client.initialized}")
            
            # List tools
            tools = list(client.tools.values())
            print(f"\nAvailable tools: {len(tools)}")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
            
            # Call hello_world tool
            if "hello_world" in client.tools:
                print("\nCalling hello_world tool...")
                result = await client.call_tool("hello_world")
                print(f"Result: {result}")
            
            print("\nTest completed successfully!")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_websocket_client())