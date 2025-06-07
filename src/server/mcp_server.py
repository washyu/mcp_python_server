"""
Modern MCP server using FastMCP for Proxmox discovery tools.
"""

import asyncio
import logging
from typing import Any, Dict, List
from mcp.server import FastMCP
from mcp.types import TextContent
from src.tools.proxmox_discovery import PROXMOX_TOOLS, handle_proxmox_tool
from src.tools.vm_creation import (
    create_vm_tool,
    start_vm_tool,
    stop_vm_tool,
    delete_vm_tool,
    get_vm_status_tool
)

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
        
        # Register VM creation tool
        self.mcp.tool(
            name="create_vm",
            description="Create a new VM from cloud-init template with automatic resource placement"
        )(self._create_vm_handler)
        
        # Register VM lifecycle management tools
        self.mcp.tool(
            name="start_vm",
            description="Start a stopped VM"
        )(self._start_vm_handler)
        
        self.mcp.tool(
            name="stop_vm",
            description="Stop a running VM gracefully or forcefully"
        )(self._stop_vm_handler)
        
        self.mcp.tool(
            name="delete_vm",
            description="Delete a VM permanently"
        )(self._delete_vm_handler)
        
        self.mcp.tool(
            name="get_vm_status",
            description="Get current status and details of a VM"
        )(self._get_vm_status_handler)
        
        logger.info(f"Successfully registered {len(PROXMOX_TOOLS) + 5} tools (including VM management)")
    
    async def _create_vm_handler(self, **kwargs) -> List[TextContent]:
        """Handle VM creation requests."""
        try:
            result = await create_vm_tool(**kwargs)
            
            if result.get("success"):
                message = f"✅ {result['message']}\n"
                message += f"VM ID: {result['vm_id']}\n"
                message += f"Node: {result['node']}\n"
                if result.get('ip_address'):
                    message += f"IP Address: {result['ip_address']}\n"
                    message += f"SSH Access: {result['ssh_access']}\n"
                message += f"Services: {', '.join(result.get('services', []))}"
            else:
                message = f"❌ {result['message']}\n"
                message += f"Error: {result.get('error', 'Unknown error')}"
            
            return [TextContent(type="text", text=message)]
            
        except Exception as e:
            error_message = f"❌ Failed to create VM: {str(e)}"
            return [TextContent(type="text", text=error_message)]
    
    async def _start_vm_handler(self, **kwargs) -> List[TextContent]:
        """Handle VM start requests."""
        try:
            result = await start_vm_tool(**kwargs)
            
            if result.get("success"):
                message = f"✅ {result['message']}\n"
                message += f"Node: {result['node']}"
            else:
                message = f"❌ {result['message']}"
            
            return [TextContent(type="text", text=message)]
            
        except Exception as e:
            error_message = f"❌ Failed to start VM: {str(e)}"
            return [TextContent(type="text", text=error_message)]
    
    async def _stop_vm_handler(self, **kwargs) -> List[TextContent]:
        """Handle VM stop requests."""
        try:
            result = await stop_vm_tool(**kwargs)
            
            if result.get("success"):
                message = f"✅ {result['message']}\n"
                message += f"Node: {result['node']}\n"
                message += f"Action: {result.get('action', 'stop')}"
            else:
                message = f"❌ {result['message']}"
            
            return [TextContent(type="text", text=message)]
            
        except Exception as e:
            error_message = f"❌ Failed to stop VM: {str(e)}"
            return [TextContent(type="text", text=error_message)]
    
    async def _delete_vm_handler(self, **kwargs) -> List[TextContent]:
        """Handle VM deletion requests."""
        try:
            result = await delete_vm_tool(**kwargs)
            
            if result.get("success"):
                message = f"✅ {result['message']}\n"
                message += f"Node: {result['node']}\n"
                message += f"Purged: {'Yes' if result.get('purged') else 'No'}"
            else:
                message = f"❌ {result['message']}"
            
            return [TextContent(type="text", text=message)]
            
        except Exception as e:
            error_message = f"❌ Failed to delete VM: {str(e)}"
            return [TextContent(type="text", text=error_message)]
    
    async def _get_vm_status_handler(self, **kwargs) -> List[TextContent]:
        """Handle VM status requests."""
        try:
            result = await get_vm_status_tool(**kwargs)
            
            if result.get("success"):
                message = f"VM {result['vm_id']} Status:\n"
                message += f"Name: {result.get('name', 'N/A')}\n"
                message += f"Node: {result['node']}\n"
                message += f"Status: {result['status']}\n"
                message += f"CPU Usage: {result.get('cpu', 0):.1%}\n"
                message += f"Memory: {result.get('memory', 0) / (1024**3):.1f}GB / {result.get('max_memory', 0) / (1024**3):.1f}GB\n"
                message += f"Disk: {result.get('disk', 0) / (1024**3):.1f}GB / {result.get('max_disk', 0) / (1024**3):.1f}GB\n"
                
                if result.get('uptime', 0) > 0:
                    uptime_hours = result['uptime'] / 3600
                    message += f"Uptime: {uptime_hours:.1f} hours\n"
                
                if result.get('ip_address'):
                    message += f"IP Address: {result['ip_address']}"
            else:
                message = f"❌ {result.get('message', 'Failed to get VM status')}\n"
                message += f"Error: {result.get('error', 'Unknown error')}"
            
            return [TextContent(type="text", text=message)]
            
        except Exception as e:
            error_message = f"❌ Failed to get VM status: {str(e)}"
            return [TextContent(type="text", text=error_message)]
    
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