"""
Universal Homelab MCP Server - Infrastructure Automation Toolkit for AI Agents

This MCP server provides tools that enable ANY AI agent to automatically:
- Discover and assess hardware capabilities
- Install and configure virtualization platforms (Proxmox, LXD, Docker)
- Deploy services with smart defaults and best practices
- Troubleshoot and optimize homelab infrastructure
- Make informed technology choices with comparative analysis

Primary Purpose: Let AI agents build complete homelab environments autonomously
with minimal human intervention, while educating users about the decisions made.
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
from src.tools.homelab_tools import HOMELAB_TOOLS, handle_homelab_tool
from src.tools.lxd_tools import LXD_TOOLS, handle_lxd_tool
from src.tools.agent_homelab_tools import AGENT_HOMELAB_TOOLS, handle_agent_homelab_tool
from src.tools.homelab_context_tools import HOMELAB_CONTEXT_TOOLS, handle_homelab_context_tool
from src.tools.ansible_tools import ANSIBLE_TOOLS, handle_ansible_tool
from src.tools.auth_setup_tools import AUTH_SETUP_TOOLS, handle_auth_setup_tool

logger = logging.getLogger(__name__)


class HomelabMCPServer:
    """
    Universal Homelab MCP Server - Infrastructure Automation Toolkit
    
    Enables ANY AI agent to automatically provision, configure, and manage
    complete homelab environments with minimal human intervention.
    
    Core Capabilities:
    - Autonomous infrastructure setup (Proxmox, LXD, Docker)
    - Smart technology selection with comparative analysis
    - Service deployment with industry best practices
    - Educational explanations of all decisions made
    """
    
    def __init__(self, name: str = "universal-homelab-mcp", host: str = "127.0.0.1", port: int = 8000):
        """Initialize the MCP server."""
        self.name = name
        self.mcp = FastMCP(name, host=host, port=port)
        self._register_tools()
    
    def _register_tools(self):
        """Register all MCP tools for AI-driven homelab automation."""
        logger.info("Registering Universal Homelab MCP tools...")
        
        # PRIORITY 0: Authentication setup tools (foundational)
        for tool in AUTH_SETUP_TOOLS:
            logger.info(f"Registering Auth tool: {tool.name}")
            
            def make_auth_handler(tool_name: str):
                async def handler(**kwargs) -> List[TextContent]:
                    return await handle_auth_setup_tool(tool_name, kwargs)
                return handler
            
            self.mcp.tool(tool.name, tool.description, tool.inputSchema)(
                make_auth_handler(tool.name)
            )
        
        # PRIORITY 1: Agent-driven automation tools (main feature)
        for tool in AGENT_HOMELAB_TOOLS:
            logger.info(f"Registering Agent tool: {tool.name}")
            
            def make_agent_handler(tool_name: str):
                async def handler(**kwargs) -> List[TextContent]:
                    return await handle_agent_homelab_tool(tool_name, kwargs)
                return handler
            
            self.mcp.tool(tool.name, tool.description, tool.inputSchema)(
                make_agent_handler(tool.name)
            )
        
        # PRIORITY 2: Homelab Context and Topology Management
        for tool in HOMELAB_CONTEXT_TOOLS:
            logger.info(f"Registering Context tool: {tool.name}")
            
            def make_context_handler(tool_name: str):
                async def handler(**kwargs) -> List[TextContent]:
                    return await handle_homelab_context_tool(tool_name, kwargs)
                return handler
            
            self.mcp.tool(tool.name, tool.description, tool.inputSchema)(
                make_context_handler(tool.name)
            )
        
        # PRIORITY 3: Infrastructure discovery and management tools
        for tool in PROXMOX_TOOLS:
            logger.info(f"Registering Infrastructure tool: {tool.name}")
            
            def make_proxmox_handler(tool_name: str):
                async def handler(**kwargs) -> List[TextContent]:
                    return await handle_proxmox_tool(tool_name, kwargs)
                return handler
            
            self.mcp.tool(tool.name, tool.description, tool.inputSchema)(
                make_proxmox_handler(tool.name)
            )
        
        # PRIORITY 4: Container platform tools  
        for tool in LXD_TOOLS:
            logger.info(f"Registering Container tool: {tool.name}")
            
            def make_lxd_handler(tool_name: str):
                async def handler(**kwargs) -> List[TextContent]:
                    return await handle_lxd_tool(tool_name, kwargs)
                return handler
            
            self.mcp.tool(tool.name, tool.description, tool.inputSchema)(
                make_lxd_handler(tool.name)
            )
        
        # PRIORITY 5: Ansible automation tools (generic service deployment)
        for tool in ANSIBLE_TOOLS:
            logger.info(f"Registering Ansible tool: {tool.name}")
            
            def make_ansible_handler(tool_name: str):
                async def handler(**kwargs) -> List[TextContent]:
                    return await handle_ansible_tool(tool_name, kwargs)
                return handler
            
            self.mcp.tool(tool.name, tool.description, tool.inputSchema)(
                make_ansible_handler(tool.name)
            )
        
        # PRIORITY 6: User guidance tools (when agent needs human input)
        for tool in HOMELAB_TOOLS:
            logger.info(f"Registering Guidance tool: {tool.name}")
            
            def make_homelab_handler(tool_name: str):
                async def handler(**kwargs) -> List[TextContent]:
                    return await handle_homelab_tool(tool_name, kwargs)
                return handler
            
            self.mcp.tool(tool.name, tool.description, tool.inputSchema)(
                make_homelab_handler(tool.name)
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
        
        total_tools = len(AGENT_HOMELAB_TOOLS) + len(HOMELAB_CONTEXT_TOOLS) + len(PROXMOX_TOOLS) + len(LXD_TOOLS) + len(HOMELAB_TOOLS) + 5
        logger.info(f"Successfully registered {total_tools} MCP tools for AI-driven homelab automation")
        logger.info(f"  🤖 Agent Automation: {len(AGENT_HOMELAB_TOOLS)} tools (PRIMARY FEATURE)")
        logger.info(f"  🏠 Homelab Context: {len(HOMELAB_CONTEXT_TOOLS)} tools")
        logger.info(f"  🏗️  Infrastructure: {len(PROXMOX_TOOLS)} tools") 
        logger.info(f"  📦 Containers: {len(LXD_TOOLS)} tools")
        logger.info(f"  👥 User Guidance: {len(HOMELAB_TOOLS)} tools")
        logger.info(f"  🖥️  VM Management: 5 tools")
    
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
        await self.mcp.run_stdio_async()
    
    async def run_sse(self, mount_path: str | None = None):
        """Run the MCP server with SSE transport."""
        logger.info(f"Starting {self.name} with SSE transport on {self.mcp.settings.host}:{self.mcp.settings.port}...")
        await self.mcp.run_sse_async(mount_path=mount_path)
    
    async def run_streamable_http(self):
        """Run the MCP server with streamable HTTP transport."""
        logger.info(f"Starting {self.name} with streamable HTTP transport on {self.mcp.settings.host}:{self.mcp.settings.port}...")
        await self.mcp.run_streamable_http_async()


async def main():
    """Main entry point for the MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    server = HomelabMCPServer()
    
    # Default to stdio transport for MCP compatibility
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())