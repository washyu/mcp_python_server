"""
Generic Ansible MCP tools for infrastructure automation.
Provides tools to execute arbitrary Ansible playbooks and commands.
"""

from typing import Any, Dict, List, Optional
from mcp.types import Tool, TextContent
import json
import yaml
import logging
from pathlib import Path

from ..utils.ansible_runner import AnsibleRunner
from ..security.credential_manager import get_credential_manager

logger = logging.getLogger(__name__)


# Service installation templates
SERVICE_TEMPLATES = {
    "react": {
        "name": "Install React development environment",
        "tasks": [
            {
                "name": "Update package cache",
                "apt": {
                    "update_cache": "yes"
                },
                "become": True
            },
            {
                "name": "Install Node.js and npm",
                "apt": {
                    "name": ["nodejs", "npm"],
                    "state": "present"
                },
                "become": True
            },
            {
                "name": "Create app directory",
                "file": {
                    "path": "/opt/react-app",
                    "state": "directory",
                    "mode": "0755"
                }
            },
            {
                "name": "Create React app",
                "shell": "cd /opt/react-app && npx create-react-app my-app --yes",
                "args": {
                    "creates": "/opt/react-app/my-app"
                }
            },
            {
                "name": "Install PM2 globally",
                "npm": {
                    "name": "pm2",
                    "global": True
                },
                "become": True
            },
            {
                "name": "Start React app with PM2",
                "shell": "cd /opt/react-app/my-app && pm2 start 'npm start' --name react-app",
                "args": {
                    "creates": "/home/{{ ansible_user }}/.pm2/pids/react-app-0.pid"
                }
            }
        ]
    },
    "docker": {
        "name": "Install Docker",
        "tasks": [
            {
                "name": "Install dependencies",
                "apt": {
                    "name": ["apt-transport-https", "ca-certificates", "curl", "gnupg", "lsb-release"],
                    "state": "present",
                    "update_cache": True
                },
                "become": True
            },
            {
                "name": "Add Docker GPG key",
                "apt_key": {
                    "url": "https://download.docker.com/linux/ubuntu/gpg",
                    "state": "present"
                },
                "become": True
            },
            {
                "name": "Add Docker repository",
                "apt_repository": {
                    "repo": "deb [arch=amd64] https://download.docker.com/linux/ubuntu {{ ansible_distribution_release }} stable",
                    "state": "present"
                },
                "become": True
            },
            {
                "name": "Install Docker",
                "apt": {
                    "name": ["docker-ce", "docker-ce-cli", "containerd.io"],
                    "state": "present",
                    "update_cache": True
                },
                "become": True
            },
            {
                "name": "Add user to docker group",
                "user": {
                    "name": "{{ ansible_user }}",
                    "groups": "docker",
                    "append": True
                },
                "become": True
            }
        ]
    },
    "pihole": {
        "name": "Install Pi-hole",
        "tasks": [
            {
                "name": "Download Pi-hole installer",
                "get_url": {
                    "url": "https://install.pi-hole.net",
                    "dest": "/tmp/install-pihole.sh",
                    "mode": "0755"
                }
            },
            {
                "name": "Run Pi-hole installer",
                "shell": "/tmp/install-pihole.sh --unattended",
                "become": True,
                "environment": {
                    "PIHOLE_INTERFACE": "eth0",
                    "IPV4_ADDRESS": "{{ ansible_default_ipv4.address }}/24",
                    "PIHOLE_DNS_1": "8.8.8.8",
                    "PIHOLE_DNS_2": "8.8.4.4",
                    "QUERY_LOGGING": "true",
                    "INSTALL_WEB": "true"
                }
            }
        ]
    },
    "nginx": {
        "name": "Install Nginx web server",
        "tasks": [
            {
                "name": "Install Nginx",
                "apt": {
                    "name": "nginx",
                    "state": "present",
                    "update_cache": True
                },
                "become": True
            },
            {
                "name": "Start and enable Nginx",
                "systemd": {
                    "name": "nginx",
                    "state": "started",
                    "enabled": True
                },
                "become": True
            }
        ]
    }
}


# Tool definitions
ANSIBLE_TOOLS = [
    Tool(
        name="run-ansible-playbook",
        description="Execute an Ansible playbook on target hosts",
        inputSchema={
            "type": "object",
            "properties": {
                "playbook": {
                    "oneOf": [
                        {
                            "type": "string",
                            "description": "Path to playbook file"
                        },
                        {
                            "type": "object",
                            "description": "Inline playbook definition"
                        }
                    ]
                },
                "hosts": {
                    "type": "string",
                    "description": "Target host(s) - can be hostname, IP, or comma-separated list"
                },
                "extra_vars": {
                    "type": "object",
                    "description": "Extra variables to pass to playbook"
                },
                "ssh_user": {
                    "type": "string",
                    "description": "SSH user for connection",
                    "default": "ansible-admin"
                }
            },
            "required": ["playbook", "hosts"]
        }
    ),
    Tool(
        name="run-ansible-command",
        description="Run an ad-hoc Ansible command on target hosts",
        inputSchema={
            "type": "object",
            "properties": {
                "hosts": {
                    "type": "string",
                    "description": "Target host(s) - can be hostname, IP, or 'all'"
                },
                "module": {
                    "type": "string",
                    "description": "Ansible module to use (e.g., 'shell', 'apt', 'service')"
                },
                "args": {
                    "type": "string",
                    "description": "Module arguments"
                },
                "become": {
                    "type": "boolean",
                    "description": "Use sudo/become",
                    "default": False
                },
                "ssh_user": {
                    "type": "string",
                    "description": "SSH user for connection",
                    "default": "ansible-admin"
                }
            },
            "required": ["hosts", "module"]
        }
    ),
    Tool(
        name="install-service-ansible",
        description="Install a service using predefined or custom Ansible playbook",
        inputSchema={
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service name (react, docker, nginx, pihole) or 'custom'"
                },
                "host": {
                    "type": "string",
                    "description": "Target host to install service on"
                },
                "custom_playbook": {
                    "type": "object",
                    "description": "Custom playbook definition (if service='custom')"
                },
                "variables": {
                    "type": "object",
                    "description": "Variables to pass to the playbook"
                },
                "ssh_user": {
                    "type": "string",
                    "description": "SSH user for connection",
                    "default": "ansible-admin"
                }
            },
            "required": ["service", "host"]
        }
    ),
    Tool(
        name="list-ansible-templates",
        description="List available service installation templates",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    )
]


async def handle_ansible_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle Ansible tool execution."""
    try:
        runner = AnsibleRunner()
        
        if name == "run-ansible-playbook":
            # Handle playbook execution
            playbook = arguments["playbook"]
            hosts = arguments["hosts"]
            extra_vars = arguments.get("extra_vars", {})
            ssh_user = arguments.get("ssh_user", "ansible-admin")
            
            # Build inventory
            inventory = {}
            for host in hosts.split(","):
                host = host.strip()
                inventory[host] = {
                    "ansible_host": host,
                    "ansible_user": ssh_user
                }
            
            # If playbook is a string (file path), read it
            if isinstance(playbook, str):
                playbook_path = Path(playbook)
                if playbook_path.exists():
                    with open(playbook_path) as f:
                        playbook_content = yaml.safe_load(f)
                        if isinstance(playbook_content, list):
                            playbook = playbook_content[0]
                        else:
                            playbook = playbook_content
                else:
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "error": f"Playbook file not found: {playbook}",
                            "suggestion": "Provide an inline playbook definition or valid file path"
                        }, indent=2)
                    )]
            
            # Ensure playbook has hosts defined
            if "hosts" not in playbook:
                playbook["hosts"] = "all"
            
            result = await runner.run_playbook_dict(
                playbook=playbook,
                inventory=inventory,
                extra_vars=extra_vars
            )
            
        elif name == "run-ansible-command":
            # Handle ad-hoc command
            hosts = arguments["hosts"]
            module = arguments["module"]
            args = arguments.get("args")
            become = arguments.get("become", False)
            ssh_user = arguments.get("ssh_user", "ansible-admin")
            
            # Build inventory
            inventory = {}
            for host in hosts.split(","):
                host = host.strip()
                inventory[host] = {
                    "ansible_host": host,
                    "ansible_user": ssh_user,
                    "ansible_become": become
                }
            
            result = await runner.run_ad_hoc_command(
                hosts="all",
                module=module,
                args=args,
                inventory=inventory
            )
            
        elif name == "install-service-ansible":
            # Handle service installation
            service = arguments["service"]
            host = arguments["host"]
            ssh_user = arguments.get("ssh_user", "ansible-admin")
            variables = arguments.get("variables", {})
            
            if service == "custom":
                # Use custom playbook
                playbook = arguments.get("custom_playbook")
                if not playbook:
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "error": "custom_playbook required when service='custom'"
                        }, indent=2)
                    )]
            else:
                # Use predefined template
                template = SERVICE_TEMPLATES.get(service)
                if not template:
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "error": f"Unknown service: {service}",
                            "available_services": list(SERVICE_TEMPLATES.keys())
                        }, indent=2)
                    )]
                
                playbook = {
                    "name": template["name"],
                    "hosts": "all",
                    "tasks": template["tasks"]
                }
            
            # Build inventory
            inventory = {
                host: {
                    "ansible_host": host,
                    "ansible_user": ssh_user
                }
            }
            
            result = await runner.run_playbook_dict(
                playbook=playbook,
                inventory=inventory,
                extra_vars=variables
            )
            
        elif name == "list-ansible-templates":
            # List available templates
            templates = {}
            for name, template in SERVICE_TEMPLATES.items():
                templates[name] = {
                    "description": template["name"],
                    "tasks": len(template["tasks"])
                }
            
            result = {
                "available_templates": templates,
                "usage": "Use install-service-ansible with service='<template_name>' or service='custom'"
            }
            
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        # Format result
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
        
    except Exception as e:
        logger.error(f"Ansible tool error: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": str(e),
                "tool": name,
                "arguments": arguments
            }, indent=2)
        )]