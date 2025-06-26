#!/usr/bin/env python3
"""
MCP (Model Context Protocol) server for homelab system management.
"""

import asyncio
import json
import sys
from typing import Any, Dict, Optional

from .tools import get_available_tools, execute_tool
from .ssh_tools import ensure_mcp_ssh_key


class HomelabMCPServer:
    """MCP Server for homelab system discovery and monitoring."""
    
    def __init__(self):
        self.tools = get_available_tools()
        self.ssh_key_initialized = False
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP requests."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                # Initialize SSH key on first request
                if not self.ssh_key_initialized:
                    await ensure_mcp_ssh_key()
                    self.ssh_key_initialized = True
                
                return self._success_response(request_id, {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "homelab-mcp",
                        "version": "0.1.0"
                    }
                })
            
            elif method == "tools/list":
                # Add the name field to each tool
                tools_list = []
                for name, tool_def in self.tools.items():
                    tool_with_name = tool_def.copy()
                    tool_with_name["name"] = name
                    tools_list.append(tool_with_name)
                return self._success_response(request_id, {"tools": tools_list})
            
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                
                if tool_name not in self.tools:
                    return self._error_response(request_id, f"Unknown tool: {tool_name}")
                
                result = await execute_tool(tool_name, tool_args)
                return self._success_response(request_id, result)
            
            else:
                return self._error_response(request_id, f"Unknown method: {method}")
                
        except Exception as e:
            return self._error_response(request_id, str(e))
    
    def _success_response(self, request_id: Any, result: Any) -> Dict[str, Any]:
        """Create a successful JSON-RPC response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
    
    def _error_response(self, request_id: Any, message: str, code: int = -32603) -> Dict[str, Any]:
        """Create an error JSON-RPC response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
    
    async def run_stdio(self):
        """Run the MCP server using stdio (stdin/stdout)."""
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
        
        while True:
            try:
                # Read line from stdin
                line_bytes = await reader.readline()
                if not line_bytes:
                    break
                    
                line = line_bytes.decode('utf-8').strip()
                if not line:
                    continue
                
                # Parse JSON-RPC request
                request = json.loads(line)
                
                # Check if this is a notification (no id field)
                if "id" not in request:
                    # Notifications don't get responses, just process them
                    method = request.get("method")
                    if method == "notifications/initialized":
                        # Client is ready, we can proceed
                        pass
                    # Don't send any response for notifications
                    continue
                
                # Handle request
                response = await self.handle_request(request)
                
                # Send response to stdout
                print(json.dumps(response))
                sys.stdout.flush()
                
            except json.JSONDecodeError as e:
                error_response = self._error_response(None, f"Invalid JSON: {str(e)}", -32700)
                print(json.dumps(error_response))
                sys.stdout.flush()
            except Exception as e:
                error_response = self._error_response(None, f"Server error: {str(e)}")
                print(json.dumps(error_response))
                sys.stdout.flush()


async def main():
    """Main entry point."""
    server = HomelabMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())