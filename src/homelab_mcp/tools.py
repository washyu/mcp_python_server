"""Tool definitions and execution for the Homelab MCP server."""

from typing import Any, Dict

from .ssh_tools import ssh_discover_system


# Tool registry
TOOLS = {
    "hello_world": {
        "description": "Returns a greeting from the homelab MCP server",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "ssh_discover": {
        "description": "SSH into a system and gather hardware/system information",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hostname": {
                    "type": "string",
                    "description": "Hostname or IP address"
                },
                "username": {
                    "type": "string", 
                    "description": "SSH username"
                },
                "password": {
                    "type": "string",
                    "description": "SSH password (if not using key)"
                },
                "key_path": {
                    "type": "string",
                    "description": "Path to SSH private key"
                }
            },
            "required": ["hostname", "username"]
        }
    }
}


def get_available_tools() -> Dict[str, Dict[str, Any]]:
    """Return all available tools with their schemas."""
    return TOOLS.copy()


async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool by name with the given arguments."""
    if tool_name == "hello_world":
        return {"content": [{"type": "text", "text": "Hello from the Homelab MCP server!"}]}
    
    elif tool_name == "ssh_discover":
        result = await ssh_discover_system(**arguments)
        return {"content": [{"type": "text", "text": result}]}
    
    else:
        raise ValueError(f"Unknown tool: {tool_name}")