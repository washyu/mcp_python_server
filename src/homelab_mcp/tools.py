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
    "deploy_infrastructure": {
        "description": "Deploy new infrastructure based on AI recommendations or user specifications",
        "inputSchema": {
            "type": "object",
            "properties": {
                "deployment_plan": {
                    "type": "object",
                    "description": "Infrastructure deployment plan",
                    "properties": {
                        "services": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {"type": "string", "enum": ["docker", "lxd", "service"]},
                                    "target_device_id": {"type": "integer"},
                                    "config": {"type": "object"}
                                },
                                "required": ["name", "type", "target_device_id"]
                            }
                        },
                        "network_changes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "action": {"type": "string", "enum": ["create_vlan", "configure_firewall", "setup_routing"]},
                                    "target_device_id": {"type": "integer"},
                                    "config": {"type": "object"}
                                }
                            }
                        }
                    }
                },
                "validate_only": {
                    "type": "boolean",
                    "default": False,
                    "description": "Only validate the plan without executing"
                }
            },
            "required": ["deployment_plan"]
        }
    },
    "update_device_config": {
        "description": "Update configuration of an existing device",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "integer",
                    "description": "Database ID of the device to update"
                },
                "config_changes": {
                    "type": "object",
                    "description": "Configuration changes to apply",
                    "properties": {
                        "services": {
                            "type": "object",
                            "description": "Service configuration changes"
                        },
                        "network": {
                            "type": "object",
                            "description": "Network configuration changes"
                        },
                        "security": {
                            "type": "object",
                            "description": "Security configuration changes"
                        },
                        "resources": {
                            "type": "object",
                            "description": "Resource allocation changes"
                        }
                    }
                },
                "backup_before_change": {
                    "type": "boolean",
                    "default": True,
                    "description": "Create backup before applying changes"
                },
                "validate_only": {
                    "type": "boolean",
                    "default": False,
                    "description": "Only validate changes without applying"
                }
            },
            "required": ["device_id", "config_changes"]
        }
    },
    "decommission_device": {
        "description": "Safely remove a device from the network infrastructure",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "integer",
                    "description": "Database ID of the device to decommission"
                },
                "migration_plan": {
                    "type": "object",
                    "description": "Plan for migrating services to other devices",
                    "properties": {
                        "target_devices": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Device IDs to migrate services to"
                        },
                        "service_mapping": {
                            "type": "object",
                            "description": "Mapping of services to target devices"
                        }
                    }
                },
                "force_removal": {
                    "type": "boolean",
                    "default": False,
                    "description": "Force removal without migration (data loss possible)"
                },
                "validate_only": {
                    "type": "boolean",
                    "default": False,
                    "description": "Only validate decommission plan without executing"
                }
            },
            "required": ["device_id"]
        }
    },
    "scale_services": {
        "description": "Scale services up or down based on resource analysis",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scaling_plan": {
                    "type": "object",
                    "description": "Service scaling plan",
                    "properties": {
                        "scale_up": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "device_id": {"type": "integer"},
                                    "service_name": {"type": "string"},
                                    "target_replicas": {"type": "integer"},
                                    "resource_allocation": {"type": "object"}
                                }
                            }
                        },
                        "scale_down": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "device_id": {"type": "integer"},
                                    "service_name": {"type": "string"},
                                    "target_replicas": {"type": "integer"}
                                }
                            }
                        }
                    }
                },
                "validate_only": {
                    "type": "boolean",
                    "default": False,
                    "description": "Only validate scaling plan without executing"
                }
            },
            "required": ["scaling_plan"]
        }
    },
    "validate_infrastructure_changes": {
        "description": "Validate infrastructure changes before applying them",
        "inputSchema": {
            "type": "object",
            "properties": {
                "change_plan": {
                    "type": "object",
                    "description": "Infrastructure change plan to validate"
                },
                "validation_level": {
                    "type": "string",
                    "enum": ["basic", "comprehensive", "simulation"],
                    "default": "comprehensive",
                    "description": "Level of validation to perform"
                }
            },
            "required": ["change_plan"]
        }
    },
    "create_infrastructure_backup": {
        "description": "Create a backup of current infrastructure state",
        "inputSchema": {
            "type": "object",
            "properties": {
                "backup_scope": {
                    "type": "string",
                    "enum": ["full", "partial", "device_specific"],
                    "default": "full",
                    "description": "Scope of the backup"
                },
                "device_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Specific device IDs to backup (for partial/device_specific)"
                },
                "include_data": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include application data in backup"
                },
                "backup_name": {
                    "type": "string",
                    "description": "Name for the backup (auto-generated if not provided)"
                }
            },
            "required": []
        }
    },
    "rollback_infrastructure_changes": {
        "description": "Rollback recent infrastructure changes",
        "inputSchema": {
            "type": "object",
            "properties": {
                "backup_id": {
                    "type": "string",
                    "description": "Backup ID to rollback to"
                },
                "rollback_scope": {
                    "type": "string",
                    "enum": ["full", "partial", "device_specific"],
                    "default": "full",
                    "description": "Scope of the rollback"
                },
                "device_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Specific device IDs to rollback (for partial/device_specific)"
                },
                "validate_only": {
                    "type": "boolean",
                    "default": False,
                    "description": "Only validate rollback plan without executing"
                }
            },
            "required": ["backup_id"]
        }
    },
    "deploy_vm": {
        "description": "Deploy a new VM/container on a specific device",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "integer",
                    "description": "Database ID of the target device"
                },
                "platform": {
                    "type": "string",
                    "enum": ["docker", "lxd"],
                    "description": "VM platform to use (docker or lxd)"
                },
                "vm_name": {
                    "type": "string",
                    "description": "Name for the new VM/container"
                },
                "vm_config": {
                    "type": "object",
                    "description": "VM configuration",
                    "properties": {
                        "image": {
                            "type": "string",
                            "description": "Container/VM image to use"
                        },
                        "ports": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Port mappings (e.g., '80:80')"
                        },
                        "volumes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Volume mounts (e.g., '/host/path:/container/path')"
                        },
                        "environment": {
                            "type": "object",
                            "description": "Environment variables"
                        },
                        "command": {
                            "type": "string",
                            "description": "Command to run in container"
                        }
                    }
                }
            },
            "required": ["device_id", "platform", "vm_name"]
        }
    },
    "control_vm": {
        "description": "Control VM state (start, stop, restart)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "integer",
                    "description": "Database ID of the target device"
                },
                "platform": {
                    "type": "string",
                    "enum": ["docker", "lxd"],
                    "description": "VM platform"
                },
                "vm_name": {
                    "type": "string",
                    "description": "Name of the VM/container"
                },
                "action": {
                    "type": "string",
                    "enum": ["start", "stop", "restart"],
                    "description": "Action to perform"
                }
            },
            "required": ["device_id", "platform", "vm_name", "action"]
        }
    },
    "get_vm_status": {
        "description": "Get detailed status of a specific VM",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "integer",
                    "description": "Database ID of the target device"
                },
                "platform": {
                    "type": "string",
                    "enum": ["docker", "lxd"],
                    "description": "VM platform"
                },
                "vm_name": {
                    "type": "string",
                    "description": "Name of the VM/container"
                }
            },
            "required": ["device_id", "platform", "vm_name"]
        }
    },
    "list_vms": {
        "description": "List all VMs/containers on a device",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "integer",
                    "description": "Database ID of the target device"
                },
                "platforms": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["docker", "lxd"]
                    },
                    "description": "Platforms to check (default: ['docker', 'lxd'])"
                }
            },
            "required": ["device_id"]
        }
    },
    "get_vm_logs": {
        "description": "Get logs from a specific VM/container",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "integer",
                    "description": "Database ID of the target device"
                },
                "platform": {
                    "type": "string",
                    "enum": ["docker", "lxd"],
                    "description": "VM platform"
                },
                "vm_name": {
                    "type": "string",
                    "description": "Name of the VM/container"
                },
                "lines": {
                    "type": "integer",
                    "default": 100,
                    "description": "Number of log lines to retrieve"
                }
            },
            "required": ["device_id", "platform", "vm_name"]
        }
    },
    "remove_vm": {
        "description": "Remove a VM/container from a device",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "integer",
                    "description": "Database ID of the target device"
                },
                "platform": {
                    "type": "string",
                    "enum": ["docker", "lxd"],
                    "description": "VM platform"
                },
                "vm_name": {
                    "type": "string",
                    "description": "Name of the VM/container"
                },
                "force": {
                    "type": "boolean",
                    "default": False,
                    "description": "Force removal without graceful shutdown"
                }
            },
            "required": ["device_id", "platform", "vm_name"]
        }
    },
    "ssh_execute_command": {
        "description": "Execute a command on a remote system via SSH",
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
                "command": {
                    "type": "string",
                    "description": "Command to execute on the remote system"
                },
                "sudo": {
                    "type": "boolean",
                    "default": False,
                    "description": "Execute command with sudo privileges"
                },
                "port": {
                    "type": "integer",
                    "description": "SSH port (default: 22)",
                    "default": 22
                }
            },
            "required": ["hostname", "username", "command"]
        }
    },
    "update_mcp_admin_groups": {
        "description": "Update mcp_admin group memberships to include groups for installed services (docker, lxd, libvirt, kvm)",
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
                "port": {
                    "type": "integer",
                    "description": "SSH port (default: 22)",
                    "default": 22
                }
            },
            "required": ["hostname", "username", "password"]
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
    
    elif tool_name == "deploy_infrastructure":
        from .infrastructure_crud import deploy_infrastructure_plan
        result = await deploy_infrastructure_plan(
            deployment_plan=arguments["deployment_plan"],
            validate_only=arguments.get("validate_only", False)
        )
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "update_device_config":
        from .infrastructure_crud import update_device_configuration
        result = await update_device_configuration(
            device_id=arguments["device_id"],
            config_changes=arguments["config_changes"],
            backup_before_change=arguments.get("backup_before_change", True),
            validate_only=arguments.get("validate_only", False)
        )
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "decommission_device":
        from .infrastructure_crud import decommission_network_device
        result = await decommission_network_device(
            device_id=arguments["device_id"],
            migration_plan=arguments.get("migration_plan"),
            force_removal=arguments.get("force_removal", False),
            validate_only=arguments.get("validate_only", False)
        )
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "scale_services":
        from .infrastructure_crud import scale_infrastructure_services
        result = await scale_infrastructure_services(
            scaling_plan=arguments["scaling_plan"],
            validate_only=arguments.get("validate_only", False)
        )
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "validate_infrastructure_changes":
        from .infrastructure_crud import validate_infrastructure_plan
        result = await validate_infrastructure_plan(
            change_plan=arguments["change_plan"],
            validation_level=arguments.get("validation_level", "comprehensive")
        )
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "create_infrastructure_backup":
        from .infrastructure_crud import create_infrastructure_backup
        result = await create_infrastructure_backup(
            backup_scope=arguments.get("backup_scope", "full"),
            device_ids=arguments.get("device_ids"),
            include_data=arguments.get("include_data", False),
            backup_name=arguments.get("backup_name")
        )
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "rollback_infrastructure_changes":
        from .infrastructure_crud import rollback_infrastructure_to_backup
        result = await rollback_infrastructure_to_backup(
            backup_id=arguments["backup_id"],
            rollback_scope=arguments.get("rollback_scope", "full"),
            device_ids=arguments.get("device_ids"),
            validate_only=arguments.get("validate_only", False)
        )
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "deploy_vm":
        from .vm_operations import deploy_vm
        result = await deploy_vm(
            device_id=arguments["device_id"],
            platform=arguments["platform"],
            vm_name=arguments["vm_name"],
            vm_config=arguments.get("vm_config", {})
        )
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "control_vm":
        from .vm_operations import control_vm_state
        result = await control_vm_state(
            device_id=arguments["device_id"],
            platform=arguments["platform"],
            vm_name=arguments["vm_name"],
            action=arguments["action"]
        )
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "get_vm_status":
        from .vm_operations import get_vm_status
        result = await get_vm_status(
            device_id=arguments["device_id"],
            platform=arguments["platform"],
            vm_name=arguments["vm_name"]
        )
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "list_vms":
        from .vm_operations import list_vms_on_device
        result = await list_vms_on_device(
            device_id=arguments["device_id"],
            platforms=arguments.get("platforms")
        )
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "get_vm_logs":
        from .vm_operations import get_vm_logs
        result = await get_vm_logs(
            device_id=arguments["device_id"],
            platform=arguments["platform"],
            vm_name=arguments["vm_name"],
            lines=arguments.get("lines", 100)
        )
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "remove_vm":
        from .vm_operations import remove_vm
        result = await remove_vm(
            device_id=arguments["device_id"],
            platform=arguments["platform"],
            vm_name=arguments["vm_name"],
            force=arguments.get("force", False)
        )
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "ssh_execute_command":
        from .ssh_tools import ssh_execute_command
        result = await ssh_execute_command(**arguments)
        return {"content": [{"type": "text", "text": result}]}
    
    elif tool_name == "update_mcp_admin_groups":
        from .ssh_tools import update_mcp_admin_groups
        result = await update_mcp_admin_groups(**arguments)
        return {"content": [{"type": "text", "text": result}]}
    
    else:
        raise ValueError(f"Unknown tool: {tool_name}")