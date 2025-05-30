"""
Simple MCP client for testing our server locally.
"""

import asyncio
import json
from typing import Any, Dict, List
import subprocess
import sys
from dataclasses import dataclass
from contextlib import asynccontextmanager


@dataclass
class Tool:
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPClient:
    """A simple MCP client that communicates with our server via subprocess."""
    
    def __init__(self, server_command: List[str]):
        self.server_command = server_command
        self.process = None
        self.tools = {}
        self._next_id = 1
        
    async def __aenter__(self):
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
    
    async def connect(self):
        """Start the MCP server subprocess and initialize connection."""
        self.process = await asyncio.create_subprocess_exec(
            *self.server_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL  # Redirect stderr to avoid output pollution
        )
        
        # Give the server a moment to start
        await asyncio.sleep(0.5)
        
        # Initialize the connection
        init_response = await self._send_request("initialize", {
            "protocolVersion": "0.1.0",
            "capabilities": {},
            "clientInfo": {
                "name": "mcp-test-client",
                "version": "0.1.0"
            }
        })
        
        # Get available tools
        response = await self._send_request("tools/list", {})
        
        if "result" in response and "tools" in response["result"]:
            for tool_data in response["result"]["tools"]:
                tool = Tool(
                    name=tool_data["name"],
                    description=tool_data["description"],
                    input_schema=tool_data.get("inputSchema", {})
                )
                self.tools[tool.name] = tool
    
    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self.process:
            self.process.terminate()
            await self.process.wait()
    
    async def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request to the server."""
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._next_id
        }
        self._next_id += 1
        
        # Send request
        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str.encode())
        await self.process.stdin.drain()
        
        # Read response with timeout
        try:
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(), 
                timeout=5.0
            )
            if not response_line:
                raise Exception("Server closed connection")
            
            response = json.loads(response_line.decode())
            return response
        except asyncio.TimeoutError:
            # Check if process is still running
            if self.process.returncode is not None:
                raise Exception(f"Server exited with code {self.process.returncode}")
            raise Exception("Timeout waiting for server response")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> str:
        """Call a tool and return the result."""
        if arguments is None:
            arguments = {}
            
        response = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        
        if "result" in response and "content" in response["result"]:
            # Extract text from content
            content = response["result"]["content"]
            if content and len(content) > 0 and content[0].get("type") == "text":
                return content[0]["text"]
        
        return f"Error calling tool: {response}"
    
    def list_tools(self) -> List[Tool]:
        """List all available tools."""
        return list(self.tools.values())


@asynccontextmanager
async def create_mcp_client():
    """Create an MCP client connected to our server."""
    # Use the Python interpreter to run our server
    server_command = [sys.executable, "main.py"]
    client = MCPClient(server_command)
    async with client:
        yield client