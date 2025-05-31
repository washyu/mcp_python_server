"""
Modern MCP server using FastMCP for Proxmox discovery tools.
"""

import asyncio
import logging
from typing import Any, Dict, List
from mcp.server import FastMCP
from mcp.types import TextContent
from src.tools.proxmox_discovery import PROXMOX_TOOLS, handle_proxmox_tool

logger = logging.getLogger(__name__)


class ProxmoxMCPServer:
    """MCP server that provides Proxmox discovery tools."""
    
    def __init__(self, name: str = "proxmox-discovery-server"):
        """Initialize the MCP server."""
        self.name = name
        self.mcp = FastMCP(name)
        self._register_tools()
    
    def _register_tools(self):
        """Register all Proxmox discovery tools."""
        logger.info("Registering Proxmox discovery tools...")
        
        for tool in PROXMOX_TOOLS:
            logger.info(f"Registering tool: {tool.name}")
            
            # Create a closure to capture the tool name
            def make_handler(tool_name: str):
                async def handler(**kwargs) -> List[TextContent]:
                    return await handle_proxmox_tool(tool_name, kwargs)
                return handler
            
            # Register the tool with FastMCP
            self.mcp.tool(tool.name, tool.description, tool.inputSchema)(
                make_handler(tool.name)
            )
        
        logger.info(f"Successfully registered {len(PROXMOX_TOOLS)} tools")
    
    async def run_stdio(self):
        """Run the MCP server with stdio transport."""
        logger.info(f"Starting {self.name} with stdio transport...")
        await self.mcp.run_stdio()
    
    async def run_sse(self, host: str = "localhost", port: int = 3000):
        """Run the MCP server with SSE transport."""
        logger.info(f"Starting {self.name} with SSE transport on {host}:{port}...")
        await self.mcp.run_sse(host=host, port=port)


async def main():
    """Main entry point for the MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    server = ProxmoxMCPServer()
    
    # Default to stdio transport for MCP compatibility
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())