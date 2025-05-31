"""
WebSocket-based MCP server implementation.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
import websockets
from websockets.server import WebSocketServerProtocol
from dataclasses import dataclass
from config import Config
from src.tools.proxmox_discovery import PROXMOX_TOOLS, handle_proxmox_tool

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Tool:
    """Represents an MCP tool."""
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPWebSocketServer:
    """MCP server that uses WebSocket transport."""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.tools: Dict[str, Tool] = {}
        self.clients: set[WebSocketServerProtocol] = set()
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self):
        """Register available tools."""
        # Register basic test tool
        self.tools["hello_world"] = Tool(
            name="hello_world",
            description="A simple tool that returns 'Hello, World!'",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            }
        )
        
        # Register Proxmox discovery tools
        for tool in PROXMOX_TOOLS:
            self.tools[tool.name] = Tool(
                name=tool.name,
                description=tool.description,
                input_schema=tool.inputSchema
            )
        
        logger.info(f"Registered {len(self.tools)} tools including {len(PROXMOX_TOOLS)} Proxmox discovery tools")
    
    async def handle_request(self, websocket: WebSocketServerProtocol, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a JSON-RPC request and return response."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                result = await self.handle_initialize(params)
            elif method == "tools/list":
                result = await self.handle_list_tools(params)
            elif method == "tools/call":
                result = await self.handle_call_tool(params)
            else:
                # Method not found
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    },
                    "id": request_id
                }
            
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }
            
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                },
                "id": request_id
            }
    
    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        return {
            "protocolVersion": "2025-03-26",
            "capabilities": {
                "experimental": {},
                "tools": {"listChanged": False}
            },
            "serverInfo": {
                "name": Config.MCP_SERVER_NAME,
                "version": Config.MCP_SERVER_VERSION
            }
        }
    
    async def handle_list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list tools request."""
        tools_list = []
        for tool in self.tools.values():
            tools_list.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            })
        
        return {"tools": tools_list}
    
    async def handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        # Call the tool
        if tool_name == "hello_world":
            result_text = "Hello, World!"
        elif tool_name.startswith("proxmox_"):
            # Call Proxmox discovery tool
            try:
                result_content = await handle_proxmox_tool(tool_name, arguments)
                
                # Convert TextContent to WebSocket format
                content = []
                for item in result_content:
                    if hasattr(item, 'text'):
                        content.append({
                            "type": "text",
                            "text": item.text
                        })
                    else:
                        content.append({
                            "type": "text", 
                            "text": str(item)
                        })
                
                return {"content": content}
                
            except Exception as e:
                logger.error(f"Error calling Proxmox tool {tool_name}: {e}")
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"❌ Error executing {tool_name}: {e}"
                        }
                    ]
                }
        else:
            result_text = f"Tool {tool_name} called with {arguments}"
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": result_text
                }
            ]
        }
    
    async def handle_client(self, websocket: WebSocketServerProtocol):
        """Handle a WebSocket client connection."""
        self.clients.add(websocket)
        logger.info(f"Client connected from {websocket.remote_address}")
        
        try:
            async for message in websocket:
                try:
                    # Parse JSON-RPC request
                    request = json.loads(message)
                    logger.debug(f"Received: {request}")
                    
                    # Handle the request
                    response = await self.handle_request(websocket, request)
                    
                    # Send response
                    await websocket.send(json.dumps(response))
                    logger.debug(f"Sent: {response}")
                    
                except json.JSONDecodeError as e:
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        },
                        "id": None
                    }
                    await websocket.send(json.dumps(error_response))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected from {websocket.remote_address}")
        finally:
            self.clients.remove(websocket)
    
    async def start(self):
        """Start the WebSocket server."""
        logger.info(f"Starting MCP WebSocket server on {self.host}:{self.port}")
        
        async with websockets.serve(self.handle_client, self.host, self.port):
            logger.info(f"Server listening on ws://{self.host}:{self.port}")
            await asyncio.Future()  # Run forever


async def main():
    """Run the WebSocket MCP server."""
    server = MCPWebSocketServer()
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())