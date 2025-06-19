"""
LXD MCP tool definitions and registration.
"""

from typing import Any, Dict, List
from mcp.types import Tool, TextContent
import json

from .lxd_discovery import get_lxd_discovery_tools
from .lxd_management import get_lxd_management_tools


# Tool definitions
LXD_TOOLS = [
    Tool(
        name="check-lxd",
        description="Check if LXD is installed and initialized on a target host",
        inputSchema={
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "Target hostname or IP address"
                },
                "ssh_user": {
                    "type": "string",
                    "description": "SSH username",
                    "default": "pi"
                },
                "ssh_port": {
                    "type": "integer",
                    "description": "SSH port",
                    "default": 22
                }
            },
            "required": ["host"]
        }
    ),
    Tool(
        name="install-lxd",
        description="Install and configure LXD on a target host if not present",
        inputSchema={
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "Target hostname or IP address"
                },
                "ssh_user": {
                    "type": "string",
                    "description": "SSH username",
                    "default": "pi"
                },
                "ssh_port": {
                    "type": "integer",
                    "description": "SSH port",
                    "default": 22
                },
                "storage_backend": {
                    "type": "string",
                    "description": "Storage backend type",
                    "enum": ["dir", "btrfs", "zfs"],
                    "default": "dir"
                },
                "storage_size": {
                    "type": "string",
                    "description": "Storage pool size",
                    "default": "20GB"
                },
                "network_address": {
                    "type": "string",
                    "description": "LXD bridge network address",
                    "default": "10.0.0.1/24"
                }
            },
            "required": ["host"]
        }
    ),
    Tool(
        name="list-lxd-containers",
        description="List all LXD containers with optional filtering",
        inputSchema={
            "type": "object",
            "properties": {
                "filter_by": {
                    "type": "string",
                    "description": "Natural language filter (e.g., 'running', 'ubuntu', 'web servers')"
                },
                "include_state": {
                    "type": "boolean",
                    "description": "Include runtime state information",
                    "default": True
                }
            }
        }
    ),
    Tool(
        name="get-lxd-container",
        description="Get detailed information about a specific LXD container",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Container name"
                }
            },
            "required": ["name"]
        }
    ),
    Tool(
        name="create-lxd-container",
        description="Create a new LXD container",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Container name"
                },
                "image": {
                    "type": "string",
                    "description": "Container image (e.g., ubuntu:22.04)",
                    "default": "ubuntu:22.04"
                },
                "cpu_limit": {
                    "type": "string",
                    "description": "CPU limit (e.g., '2' for 2 cores)"
                },
                "memory_limit": {
                    "type": "string",
                    "description": "Memory limit (e.g., '2GB')"
                },
                "disk_limit": {
                    "type": "string",
                    "description": "Disk limit (e.g., '10GB')"
                },
                "profiles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of profiles to apply"
                },
                "autostart": {
                    "type": "boolean",
                    "description": "Start container after creation",
                    "default": True
                }
            },
            "required": ["name"]
        }
    ),
    Tool(
        name="manage-lxd-container",
        description="Manage LXD container lifecycle (start, stop, restart, delete)",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Container name"
                },
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": ["start", "stop", "restart", "delete"]
                }
            },
            "required": ["name", "action"]
        }
    ),
    Tool(
        name="install-service-lxd",
        description="Install a service inside an LXD container",
        inputSchema={
            "type": "object",
            "properties": {
                "container_name": {
                    "type": "string",
                    "description": "Target container name"
                },
                "service": {
                    "type": "string",
                    "description": "Service to install",
                    "enum": ["nginx", "mysql", "docker"]
                },
                "config": {
                    "type": "object",
                    "description": "Optional service configuration"
                }
            },
            "required": ["container_name", "service"]
        }
    ),
    Tool(
        name="suggest-lxd-deployment",
        description="Get deployment suggestions for LXD containers based on workload type",
        inputSchema={
            "type": "object",
            "properties": {
                "workload_type": {
                    "type": "string",
                    "description": "Type of workload (web, database, app, development)"
                },
                "requirements": {
                    "type": "object",
                    "description": "Specific resource requirements",
                    "properties": {
                        "cpu": {"type": "integer"},
                        "memory": {"type": "string"},
                        "image": {"type": "string"}
                    }
                }
            },
            "required": ["workload_type"]
        }
    ),
    Tool(
        name="lxd-resource-usage",
        description="Get overall resource usage across all LXD containers",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="lxd-infrastructure-diagram",
        description="Generate ASCII diagram of LXD infrastructure",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="exec-in-lxd-container",
        description="Execute a command inside an LXD container",
        inputSchema={
            "type": "object",
            "properties": {
                "container_name": {
                    "type": "string",
                    "description": "Name of the container to execute command in"
                },
                "command": {
                    "type": "string",
                    "description": "Command to execute (as a single string)"
                },
                "host": {
                    "type": "string",
                    "description": "LXD host (if not localhost)"
                }
            },
            "required": ["container_name", "command"]
        }
    )
]


async def handle_lxd_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle LXD tool execution."""
    try:
        management_tools = get_lxd_management_tools()
        discovery_tools = get_lxd_discovery_tools()
        
        if name == "check-lxd":
            result = await management_tools.check_lxd_installed(
                host=arguments["host"],
                ssh_user=arguments.get("ssh_user", "pi"),
                ssh_port=arguments.get("ssh_port", 22)
            )
            
        elif name == "install-lxd":
            result = await management_tools.install_lxd(
                host=arguments["host"],
                ssh_user=arguments.get("ssh_user", "pi"),
                ssh_port=arguments.get("ssh_port", 22),
                storage_backend=arguments.get("storage_backend", "dir"),
                storage_size=arguments.get("storage_size", "20GB"),
                network_address=arguments.get("network_address", "10.0.0.1/24")
            )
            
        elif name == "list-lxd-containers":
            result = await discovery_tools.list_containers(
                filter_by=arguments.get("filter_by"),
                include_state=arguments.get("include_state", True)
            )
            
        elif name == "get-lxd-container":
            result = await discovery_tools.get_container_details(
                name=arguments["name"]
            )
            
        elif name == "create-lxd-container":
            result = await management_tools.create_container(
                name=arguments["name"],
                image=arguments.get("image", "ubuntu:22.04"),
                cpu_limit=arguments.get("cpu_limit"),
                memory_limit=arguments.get("memory_limit"),
                disk_limit=arguments.get("disk_limit"),
                profiles=arguments.get("profiles"),
                autostart=arguments.get("autostart", True)
            )
            
        elif name == "manage-lxd-container":
            result = await management_tools.manage_container(
                name=arguments["name"],
                action=arguments["action"]
            )
            
        elif name == "install-service-lxd":
            result = await management_tools.install_service_in_container(
                container_name=arguments["container_name"],
                service=arguments["service"],
                config=arguments.get("config")
            )
            
        elif name == "suggest-lxd-deployment":
            result = await discovery_tools.suggest_container_deployment(
                workload_type=arguments["workload_type"],
                requirements=arguments.get("requirements")
            )
            
        elif name == "lxd-resource-usage":
            result = await discovery_tools.get_resource_usage()
            
        elif name == "lxd-infrastructure-diagram":
            diagram = await discovery_tools.generate_infrastructure_diagram()
            return [TextContent(type="text", text=diagram)]
            
        elif name == "exec-in-lxd-container":
            # Execute command in container
            from ..utils.lxd_api import LXDAPIClient
            
            client = LXDAPIClient(
                host=arguments.get("host", "localhost"),
                verify_ssl=False
            )
            
            # Parse command string into list
            import shlex
            command_list = shlex.split(arguments["command"])
            
            result = await client.exec_in_container(
                name=arguments["container_name"],
                command=command_list
            )
            
        else:
            result = {"error": f"Unknown tool: {name}"}
            
        # Format result as JSON for consistency
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
        
    except Exception as e:
        error_result = {
            "error": str(e),
            "tool": name,
            "arguments": arguments
        }
        return [TextContent(
            type="text",
            text=json.dumps(error_result, indent=2)
        )]


def get_lxd_tools() -> List[Tool]:
    """Get all LXD tools."""
    return LXD_TOOLS