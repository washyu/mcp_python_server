"""Tool definitions and execution for the Homelab MCP server."""

from typing import Any, Dict

from .ssh_tools import ssh_discover_system, setup_remote_mcp_admin, verify_mcp_admin_access


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
                    "description": "SSH username (use 'mcp_admin' for passwordless access after setup)"
                },
                "password": {
                    "type": "string",
                    "description": "SSH password (not needed for mcp_admin after setup)"
                },
                "key_path": {
                    "type": "string",
                    "description": "Path to SSH private key"
                }
            },
            "required": ["hostname", "username"]
        }
    },
    "setup_mcp_admin": {
        "description": "SSH into a remote system and setup mcp_admin user with admin permissions and SSH key access",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hostname": {
                    "type": "string",
                    "description": "Hostname or IP address of the target system"
                },
                "username": {
                    "type": "string",
                    "description": "Admin username to connect with (must have sudo access)"
                },
                "password": {
                    "type": "string",
                    "description": "Password for the admin user"
                },
                "force_update_key": {
                    "type": "boolean",
                    "description": "Force update SSH key even if mcp_admin already has keys (default: true)",
                    "default": True
                }
            },
            "required": ["hostname", "username", "password"]
        }
    },
    "verify_mcp_admin": {
        "description": "Verify SSH key access to mcp_admin account on a remote system",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hostname": {
                    "type": "string",
                    "description": "Hostname or IP address of the target system"
                }
            },
            "required": ["hostname"]
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
    
    elif tool_name == "setup_mcp_admin":
        result = await setup_remote_mcp_admin(**arguments)
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "verify_mcp_admin":
        result = await verify_mcp_admin_access(**arguments)
        return {"content": [{"type": "text", "text": result}]}
    
    else:
        raise ValueError(f"Unknown tool: {tool_name}")