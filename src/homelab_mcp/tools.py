"""Tool definitions and execution for the Homelab MCP server."""

from typing import Any, Dict

from .ssh_tools import ssh_discover_system, setup_remote_mcp_admin, verify_mcp_admin_access
from .sitemap import NetworkSiteMap, discover_and_store, bulk_discover_and_store


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
                },
                "port": {
                    "type": "integer",
                    "description": "SSH port (default: 22)",
                    "default": 22
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
                },
                "port": {
                    "type": "integer",
                    "description": "SSH port (default: 22)",
                    "default": 22
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
                },
                "port": {
                    "type": "integer",
                    "description": "SSH port (default: 22)",
                    "default": 22
                }
            },
            "required": ["hostname"]
        }
    },
    "discover_and_map": {
        "description": "Discover a device via SSH and store it in the network site map database",
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
                },
                "port": {
                    "type": "integer",
                    "description": "SSH port (default: 22)",
                    "default": 22
                }
            },
            "required": ["hostname", "username"]
        }
    },
    "bulk_discover_and_map": {
        "description": "Discover multiple devices via SSH and store them in the network site map database",
        "inputSchema": {
            "type": "object",
            "properties": {
                "targets": {
                    "type": "array",
                    "description": "Array of target device configurations",
                    "items": {
                        "type": "object",
                        "properties": {
                            "hostname": {"type": "string"},
                            "username": {"type": "string"},
                            "password": {"type": "string"},
                            "key_path": {"type": "string"},
                            "port": {"type": "integer", "default": 22}
                        },
                        "required": ["hostname", "username"]
                    }
                }
            },
            "required": ["targets"]
        }
    },
    "get_network_sitemap": {
        "description": "Get all discovered devices from the network site map database",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "analyze_network_topology": {
        "description": "Analyze the network topology and provide insights about the discovered devices",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "suggest_deployments": {
        "description": "Suggest optimal deployment locations based on current network topology and device capabilities",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "get_device_changes": {
        "description": "Get change history for a specific device",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "integer",
                    "description": "Database ID of the device"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of changes to return (default: 10)",
                    "default": 10
                }
            },
            "required": ["device_id"]
        }
    },
    "deploy_vm": {
        "description": "Deploy a VM/container on a specified platform (Docker, LXD, Proxmox)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["docker", "lxd", "proxmox"],
                    "description": "Target platform for VM deployment"
                },
                "vm_name": {
                    "type": "string",
                    "description": "Name for the VM/container",
                    "default": "homelab-vm"
                },
                "target_host": {
                    "type": "string",
                    "description": "Target host IP address for deployment"
                },
                "ssh_user": {
                    "type": "string",
                    "description": "SSH username for target host"
                },
                "ssh_password": {
                    "type": "string",
                    "description": "SSH password for target host"
                },
                "vm_config": {
                    "type": "object",
                    "properties": {
                        "cpu_cores": {"type": "integer", "default": 2},
                        "memory_gb": {"type": "integer", "default": 2},
                        "ssh_port": {"type": "integer", "default": 22}
                    }
                }
            },
            "required": ["platform", "target_host", "ssh_user", "ssh_password"]
        }
    },
    "delete_vm": {
        "description": "Delete/destroy a VM/container on a specified platform",
        "inputSchema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["docker", "lxd", "proxmox"],
                    "description": "Platform where VM is deployed"
                },
                "vm_name": {
                    "type": "string",
                    "description": "Name of the VM/container to delete"
                },
                "target_host": {
                    "type": "string",
                    "description": "Target host IP address"
                },
                "ssh_user": {
                    "type": "string",
                    "description": "SSH username for target host"
                },
                "ssh_password": {
                    "type": "string",
                    "description": "SSH password for target host"
                }
            },
            "required": ["platform", "vm_name", "target_host", "ssh_user", "ssh_password"]
        }
    },
    "list_vms": {
        "description": "List all VMs/containers on a target host across all platforms",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_host": {
                    "type": "string",
                    "description": "Target host IP address"
                },
                "ssh_user": {
                    "type": "string",
                    "description": "SSH username for target host"
                },
                "ssh_password": {
                    "type": "string",
                    "description": "SSH password for target host"
                },
                "platforms": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["docker", "lxd", "proxmox"]},
                    "default": ["docker", "lxd"],
                    "description": "Platforms to check for VMs"
                }
            },
            "required": ["target_host", "ssh_user", "ssh_password"]
        }
    },
    "control_vm": {
        "description": "Control VM/container state (start, stop, restart)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["docker", "lxd", "proxmox"],
                    "description": "Platform where VM is deployed"
                },
                "vm_name": {
                    "type": "string",
                    "description": "Name of the VM/container to control"
                },
                "action": {
                    "type": "string",
                    "enum": ["start", "stop", "restart"],
                    "description": "Action to perform on the VM"
                },
                "target_host": {
                    "type": "string",
                    "description": "Target host IP address"
                },
                "ssh_user": {
                    "type": "string",
                    "description": "SSH username for target host"
                },
                "ssh_password": {
                    "type": "string",
                    "description": "SSH password for target host"
                }
            },
            "required": ["platform", "vm_name", "action", "target_host", "ssh_user", "ssh_password"]
        }
    },
    "get_vm_status": {
        "description": "Get detailed status and resource usage for a specific VM/container",
        "inputSchema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["docker", "lxd", "proxmox"],
                    "description": "Platform where VM is deployed"
                },
                "vm_name": {
                    "type": "string",
                    "description": "Name of the VM/container to check"
                },
                "target_host": {
                    "type": "string",
                    "description": "Target host IP address"
                },
                "ssh_user": {
                    "type": "string",
                    "description": "SSH username for target host"
                },
                "ssh_password": {
                    "type": "string",
                    "description": "SSH password for target host"
                }
            },
            "required": ["platform", "vm_name", "target_host", "ssh_user", "ssh_password"]
        }
    },
    "get_vm_logs": {
        "description": "Get logs from a VM/container",
        "inputSchema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["docker", "lxd", "proxmox"],
                    "description": "Platform where VM is deployed"
                },
                "vm_name": {
                    "type": "string",
                    "description": "Name of the VM/container"
                },
                "target_host": {
                    "type": "string",
                    "description": "Target host IP address"
                },
                "ssh_user": {
                    "type": "string",
                    "description": "SSH username for target host"
                },
                "ssh_password": {
                    "type": "string",
                    "description": "SSH password for target host"
                },
                "lines": {
                    "type": "integer",
                    "default": 50,
                    "description": "Number of log lines to retrieve"
                },
                "follow": {
                    "type": "boolean",
                    "default": False,
                    "description": "Follow logs in real-time (limited support)"
                }
            },
            "required": ["platform", "vm_name", "target_host", "ssh_user", "ssh_password"]
        }
    },
    "manage_vm_services": {
        "description": "Manage services inside a VM/container (list, start, stop, status)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["docker", "lxd", "proxmox"],
                    "description": "Platform where VM is deployed"
                },
                "vm_name": {
                    "type": "string",
                    "description": "Name of the VM/container"
                },
                "action": {
                    "type": "string",
                    "enum": ["list", "start", "stop", "restart", "status"],
                    "description": "Service management action"
                },
                "service_name": {
                    "type": "string",
                    "description": "Name of the service (required for start/stop/restart/status actions)"
                },
                "target_host": {
                    "type": "string",
                    "description": "Target host IP address"
                },
                "ssh_user": {
                    "type": "string",
                    "description": "SSH username for target host"
                },
                "ssh_password": {
                    "type": "string",
                    "description": "SSH password for target host"
                }
            },
            "required": ["platform", "vm_name", "action", "target_host", "ssh_user", "ssh_password"]
        }
    }
}


def get_available_tools() -> Dict[str, Dict[str, Any]]:
    """Return all available tools with their schemas."""
    return TOOLS.copy()


async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool by name with the given arguments."""
    # Initialize sitemap instance
    sitemap = NetworkSiteMap()
    
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
    
    elif tool_name == "discover_and_map":
        result = await discover_and_store(sitemap, **arguments)
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "bulk_discover_and_map":
        result = await bulk_discover_and_store(sitemap, arguments["targets"])
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "get_network_sitemap":
        import json
        devices = sitemap.get_all_devices()
        result = json.dumps({
            "status": "success",
            "total_devices": len(devices),
            "devices": devices
        }, indent=2)
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "analyze_network_topology":
        import json
        analysis = sitemap.analyze_network_topology()
        result = json.dumps({
            "status": "success",
            "analysis": analysis
        }, indent=2)
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "suggest_deployments":
        import json
        suggestions = sitemap.suggest_deployments()
        result = json.dumps({
            "status": "success",
            "suggestions": suggestions
        }, indent=2)
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "get_device_changes":
        import json
        changes = sitemap.get_device_changes(
            arguments["device_id"],
            arguments.get("limit", 10)
        )
        result = json.dumps({
            "status": "success",
            "device_id": arguments["device_id"],
            "changes": changes
        }, indent=2)
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "deploy_vm":
        from .vm_manager import deploy_vm_on_platform
        result = await deploy_vm_on_platform(
            platform=arguments["platform"],
            vm_name=arguments.get("vm_name", "homelab-vm"),
            target_host=arguments["target_host"],
            ssh_user=arguments["ssh_user"],
            ssh_password=arguments["ssh_password"],
            vm_config=arguments.get("vm_config", {})
        )
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "delete_vm":
        from .vm_manager import delete_vm_on_platform
        result = await delete_vm_on_platform(
            platform=arguments["platform"],
            vm_name=arguments["vm_name"],
            target_host=arguments["target_host"],
            ssh_user=arguments["ssh_user"],
            ssh_password=arguments["ssh_password"]
        )
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "list_vms":
        from .vm_manager import list_vms_on_host
        result = await list_vms_on_host(
            target_host=arguments["target_host"],
            ssh_user=arguments["ssh_user"],
            ssh_password=arguments["ssh_password"],
            platforms=arguments.get("platforms", ["docker", "lxd"])
        )
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "control_vm":
        from .vm_operations import control_vm_state
        result = await control_vm_state(
            platform=arguments["platform"],
            vm_name=arguments["vm_name"],
            action=arguments["action"],
            target_host=arguments["target_host"],
            ssh_user=arguments["ssh_user"],
            ssh_password=arguments["ssh_password"]
        )
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "get_vm_status":
        from .vm_operations import get_vm_detailed_status
        result = await get_vm_detailed_status(
            platform=arguments["platform"],
            vm_name=arguments["vm_name"],
            target_host=arguments["target_host"],
            ssh_user=arguments["ssh_user"],
            ssh_password=arguments["ssh_password"]
        )
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "get_vm_logs":
        from .vm_operations import get_vm_logs
        result = await get_vm_logs(
            platform=arguments["platform"],
            vm_name=arguments["vm_name"],
            target_host=arguments["target_host"],
            ssh_user=arguments["ssh_user"],
            ssh_password=arguments["ssh_password"],
            lines=arguments.get("lines", 50),
            follow=arguments.get("follow", False)
        )
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "manage_vm_services":
        from .vm_operations import manage_vm_services
        result = await manage_vm_services(
            platform=arguments["platform"],
            vm_name=arguments["vm_name"],
            action=arguments["action"],
            target_host=arguments["target_host"],
            ssh_user=arguments["ssh_user"],
            ssh_password=arguments["ssh_password"],
            service_name=arguments.get("service_name")
        )
        return {"content": [{"type": "text", "text": result}]}
    
    else:
        raise ValueError(f"Unknown tool: {tool_name}")