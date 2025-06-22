"""
Hardware Discovery Guide Tool
Helps AI agents choose the correct hardware discovery method.
"""

from typing import List
from mcp.types import Tool, TextContent


def register_hardware_guide_tools(server):
    """Register hardware discovery guide tool."""
    
    @server.tool()
    async def hardware_discovery_guide(
        target: str = "remote",
        ip_address: str = ""
    ) -> List[TextContent]:
        """Guide for choosing the correct hardware discovery tool.
        
        Args:
            target: "local" for MCP server, "remote" for other systems
            ip_address: IP address for remote systems
        """
        
        guide = ["🔍 **Hardware Discovery Guide**\n"]
        
        if target == "local":
            guide.append("**For LOCAL MCP server hardware:**")
            guide.append("Use: `discover_local_hardware`")
            guide.append("Example: To check the hardware where MCP is running\n")
        
        elif target == "remote" and ip_address:
            guide.append(f"**For REMOTE system at {ip_address}:**")
            guide.append(f"Use: `discover_remote_system ip_address=\"{ip_address}\"`")
            guide.append("This will:")
            guide.append("- Connect via SSH")
            guide.append("- Get CPU, memory, storage, GPU details")
            guide.append("- Update homelab context")
            guide.append("- If SSH fails, use `setup_remote_ssh_access` first\n")
        
        else:
            guide.append("**Choose the right tool:**\n")
            guide.append("1. **discover_local_hardware**")
            guide.append("   - Use for: MCP server's own hardware")
            guide.append("   - Returns: CPU, memory, storage of where MCP runs\n")
            
            guide.append("2. **discover_remote_system**")
            guide.append("   - Use for: Any other server/computer")
            guide.append("   - Required: IP address")
            guide.append("   - Returns: Full hardware specs via SSH\n")
            
            guide.append("3. **discover-homelab-topology**")
            guide.append("   - Use for: Network scanning only")
            guide.append("   - Returns: List of alive IPs (NO hardware details)\n")
            
            guide.append("**Common mistake:** Using discover-homelab-topology for hardware info")
            guide.append("**Solution:** Always use discover_remote_system for hardware specs!")
        
        return [TextContent(type="text", text="\n".join(guide))]


# Tool definition
HARDWARE_GUIDE_TOOLS = [
    Tool(
        name="hardware_discovery_guide",
        description="Get guidance on which hardware discovery tool to use",
        inputSchema={
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Target system: 'local' or 'remote'",
                    "enum": ["local", "remote"],
                    "default": "remote"
                },
                "ip_address": {
                    "type": "string",
                    "description": "IP address for remote systems"
                }
            },
            "required": []
        }
    )
]