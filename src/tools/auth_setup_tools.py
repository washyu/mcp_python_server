"""
Authentication setup tools for homelab servers.
Handles SSH key deployment, GitHub key fetching, and access verification.
"""

from typing import Any, Dict, List, Optional
from mcp.types import Tool, TextContent
import json
import asyncio
import aiohttp
import logging
from pathlib import Path

from ..utils.ansible_runner import AnsibleRunner
from ..utils.homelab_context import HomelabContextManager
from .mcp_ssh_manager import MCPSSHKeyManager
from .universal_auth_manager import UniversalAuthManager

logger = logging.getLogger(__name__)


# Tool definitions
AUTH_SETUP_TOOLS = [
    Tool(
        name="fetch-github-ssh-keys",
        description="Fetch public SSH keys from a GitHub user's profile",
        inputSchema={
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "GitHub username to fetch SSH keys from"
                },
                "key_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key types to filter (e.g., ['ssh-rsa', 'ssh-ed25519'])",
                    "default": ["ssh-ed25519", "ssh-rsa"]
                }
            },
            "required": ["username"]
        }
    ),
    Tool(
        name="deploy-ssh-keys",
        description="Deploy SSH keys to target servers for authentication",
        inputSchema={
            "type": "object",
            "properties": {
                "hosts": {
                    "type": "string",
                    "description": "Target host(s) - can be hostname, IP, or comma-separated list"
                },
                "ssh_keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "SSH public keys to deploy"
                },
                "username": {
                    "type": "string",
                    "description": "Username to deploy keys for",
                    "default": "ansible-admin"
                },
                "create_user": {
                    "type": "boolean",
                    "description": "Create the user if it doesn't exist",
                    "default": True
                },
                "sudo_access": {
                    "type": "boolean",
                    "description": "Grant sudo access to the user",
                    "default": True
                },
                "initial_auth": {
                    "type": "object",
                    "description": "Initial authentication method to use",
                    "properties": {
                        "method": {
                            "type": "string",
                            "enum": ["password", "key", "pi_default"],
                            "description": "Authentication method"
                        },
                        "password": {
                            "type": "string",
                            "description": "Password for initial access"
                        },
                        "key_path": {
                            "type": "string",
                            "description": "Path to SSH key for initial access"
                        }
                    }
                }
            },
            "required": ["hosts", "ssh_keys"]
        }
    ),
    Tool(
        name="setup-homelab-auth",
        description="Complete authentication setup for a new homelab server using GitHub SSH keys",
        inputSchema={
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "Target hostname or IP address"
                },
                "github_username": {
                    "type": "string",
                    "description": "GitHub username to fetch SSH keys from"
                },
                "ansible_user": {
                    "type": "string",
                    "description": "Username for Ansible automation",
                    "default": "ansible-admin"
                },
                "initial_auth": {
                    "type": "object",
                    "description": "How to initially connect to the server",
                    "properties": {
                        "method": {
                            "type": "string",
                            "enum": ["password", "pi_default", "existing_key"],
                            "description": "Initial authentication method"
                        },
                        "password": {
                            "type": "string",
                            "description": "Initial password (if using password auth)"
                        },
                        "username": {
                            "type": "string", 
                            "description": "Initial username (default: pi for Raspberry Pi)",
                            "default": "pi"
                        }
                    },
                    "required": ["method"]
                }
            },
            "required": ["host", "github_username", "initial_auth"]
        }
    ),
    Tool(
        name="verify-ssh-access",
        description="Verify SSH access to a server and test authentication",
        inputSchema={
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "Target hostname or IP address"
                },
                "username": {
                    "type": "string",
                    "description": "Username to test",
                    "default": "ansible-admin"
                },
                "test_sudo": {
                    "type": "boolean",
                    "description": "Test sudo access",
                    "default": True
                }
            },
            "required": ["host"]
        }
    ),
    Tool(
        name="list-server-users",
        description="List users on a target server and their authentication status",
        inputSchema={
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "Target hostname or IP address"
                },
                "check_ssh_keys": {
                    "type": "boolean",
                    "description": "Check SSH key configurations",
                    "default": True
                }
            },
            "required": ["host"]
        }
    ),
    Tool(
        name="get-authentication-context",
        description="Get authentication information stored in homelab context",
        inputSchema={
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "Specific host IP to get auth info for (optional)"
                }
            }
        }
    ),
    Tool(
        name="suggest-github-username",
        description="Suggest GitHub username from existing context or ask user",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="generate-mcp-ssh-key",
        description="Generate a dedicated SSH key pair for MCP homelab automation",
        inputSchema={
            "type": "object",
            "properties": {
                "key_type": {
                    "type": "string",
                    "enum": ["ed25519", "rsa"],
                    "description": "Type of SSH key to generate",
                    "default": "ed25519"
                },
                "key_comment": {
                    "type": "string",
                    "description": "Comment for the SSH key"
                },
                "force_regenerate": {
                    "type": "boolean",
                    "description": "Force regeneration even if key exists",
                    "default": False
                }
            }
        }
    ),
    Tool(
        name="setup-homelab-auth-mcp",
        description="Complete authentication setup using MCP-generated SSH key (recommended approach)",
        inputSchema={
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "Target hostname or IP address"
                },
                "ansible_user": {
                    "type": "string",
                    "description": "Username for Ansible automation",
                    "default": "ansible-admin"
                },
                "initial_auth": {
                    "type": "object",
                    "description": "How to initially connect to the server",
                    "properties": {
                        "method": {
                            "type": "string",
                            "enum": ["password", "pi_default", "existing_key"],
                            "description": "Initial authentication method"
                        },
                        "password": {
                            "type": "string",
                            "description": "Initial password (if using password auth)"
                        },
                        "username": {
                            "type": "string",
                            "description": "Initial username (default: pi for Raspberry Pi)",
                            "default": "pi"
                        }
                    },
                    "required": ["method"]
                },
                "auto_generate_key": {
                    "type": "boolean",
                    "description": "Automatically generate MCP SSH key if it doesn't exist",
                    "default": True
                }
            },
            "required": ["host", "initial_auth"]
        }
    ),
    Tool(
        name="get-mcp-ssh-key-info",
        description="Get information about the MCP SSH key",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="test-mcp-ssh-access",
        description="Test SSH access to a server using the MCP key",
        inputSchema={
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "Target hostname or IP address"
                },
                "user": {
                    "type": "string",
                    "description": "Username to test",
                    "default": "ansible-admin"
                }
            },
            "required": ["host"]
        }
    ),
    Tool(
        name="setup-universal-auth",
        description="Setup authentication for any infrastructure provider (Proxmox, TrueNAS, Docker, AWS, etc.)",
        inputSchema={
            "type": "object",
            "properties": {
                "provider_type": {
                    "type": "string",
                    "enum": ["proxmox", "truenas", "docker", "lxd", "vmware", "aws", "azure", "gcp", "kubernetes", "generic_ssh"],
                    "description": "Type of infrastructure provider"
                },
                "endpoint": {
                    "type": "string",
                    "description": "Host/URL for the service"
                },
                "auth_method": {
                    "type": "string",
                    "enum": ["auto", "ssh_key", "api_token", "cloud_role", "domain_account", "certificate"],
                    "description": "Authentication method (auto-detects best method)",
                    "default": "auto"
                },
                "ssh_user": {
                    "type": "string",
                    "description": "SSH username (for SSH-based auth)"
                },
                "api_token": {
                    "type": "string",
                    "description": "API token/key (for API-based auth)"
                },
                "username": {
                    "type": "string",
                    "description": "Username (for domain/API auth)"
                },
                "password": {
                    "type": "string",
                    "description": "Password (for domain auth)"
                },
                "role_arn": {
                    "type": "string",
                    "description": "AWS role ARN (for cloud role auth)"
                },
                "tenant_id": {
                    "type": "string",
                    "description": "Azure tenant ID"
                },
                "service_account": {
                    "type": "string",
                    "description": "Service account email/ID"
                },
                "initial_auth": {
                    "type": "object",
                    "description": "Initial authentication for SSH key deployment",
                    "properties": {
                        "method": {"type": "string"},
                        "username": {"type": "string"},
                        "password": {"type": "string"}
                    }
                }
            },
            "required": ["provider_type", "endpoint"]
        }
    ),
    Tool(
        name="list-auth-configurations",
        description="List all stored authentication configurations for infrastructure providers",
        inputSchema={
            "type": "object",
            "properties": {
                "provider_type": {
                    "type": "string",
                    "description": "Filter by provider type (optional)"
                }
            }
        }
    ),
    Tool(
        name="get-auth-configuration",
        description="Get authentication configuration for a specific provider and endpoint",
        inputSchema={
            "type": "object",
            "properties": {
                "provider_type": {
                    "type": "string",
                    "description": "Type of infrastructure provider"
                },
                "endpoint": {
                    "type": "string",
                    "description": "Host/URL for the service"
                }
            },
            "required": ["provider_type", "endpoint"]
        }
    )
]


class AuthSetupManager:
    """Manages authentication setup for homelab servers."""
    
    def __init__(self):
        self.ansible_runner = AnsibleRunner()
        self.context_manager = HomelabContextManager()
    
    async def fetch_github_keys(self, username: str, key_types: List[str] = None) -> Dict[str, Any]:
        """Fetch public SSH keys from GitHub user profile."""
        if key_types is None:
            key_types = ["ssh-ed25519", "ssh-rsa"]
        
        try:
            url = f"https://github.com/{username}.keys"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 404:
                        return {
                            "success": False,
                            "error": f"GitHub user '{username}' not found or has no public keys"
                        }
                    
                    response.raise_for_status()
                    keys_text = await response.text()
            
            # Parse and filter keys
            all_keys = [key.strip() for key in keys_text.strip().split('\n') if key.strip()]
            
            filtered_keys = []
            key_info = []
            
            for key in all_keys:
                if any(key.startswith(key_type) for key_type in key_types):
                    filtered_keys.append(key)
                    
                    # Extract key type and fingerprint info
                    parts = key.split()
                    if len(parts) >= 2:
                        key_type = parts[0]
                        # Simple fingerprint (last 16 chars of key)
                        fingerprint = parts[1][-16:] if len(parts[1]) > 16 else parts[1]
                        key_info.append({
                            "type": key_type,
                            "fingerprint": f"...{fingerprint}",
                            "key": key
                        })
            
            return {
                "success": True,
                "username": username,
                "total_keys": len(all_keys),
                "filtered_keys": len(filtered_keys),
                "keys": filtered_keys,
                "key_details": key_info,
                "url": url
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch GitHub keys for {username}: {e}")
            return {
                "success": False,
                "error": str(e),
                "username": username
            }
    
    async def deploy_ssh_keys(
        self,
        hosts: str,
        ssh_keys: List[str],
        username: str = "ansible-admin",
        create_user: bool = True,
        sudo_access: bool = True,
        initial_auth: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Deploy SSH keys to target servers."""
        try:
            # Build inventory with initial authentication
            inventory = {}
            for host in hosts.split(","):
                host = host.strip()
                host_config = {"ansible_host": host}
                
                if initial_auth:
                    if initial_auth.get("method") == "password":
                        host_config["ansible_user"] = initial_auth.get("username", "pi")
                        host_config["ansible_ssh_pass"] = initial_auth.get("password")
                        host_config["ansible_become_pass"] = initial_auth.get("password")
                    elif initial_auth.get("method") == "pi_default":
                        host_config["ansible_user"] = "pi"
                        # Use default Raspberry Pi authentication
                    elif initial_auth.get("method") == "existing_key":
                        host_config["ansible_user"] = initial_auth.get("username", "pi")
                        if initial_auth.get("key_path"):
                            host_config["ansible_ssh_private_key_file"] = initial_auth["key_path"]
                
                inventory[host] = host_config
            
            # Create playbook for SSH key deployment
            tasks = []
            
            # Create user if needed
            if create_user:
                tasks.append({
                    "name": f"Create user {username}",
                    "user": {
                        "name": username,
                        "state": "present",
                        "create_home": True,
                        "shell": "/bin/bash"
                    },
                    "become": True
                })
            
            # Grant sudo access if requested
            if sudo_access:
                tasks.append({
                    "name": f"Grant sudo access to {username}",
                    "copy": {
                        "dest": f"/etc/sudoers.d/{username}",
                        "content": f"{username} ALL=(ALL) NOPASSWD: ALL\n",
                        "mode": "0440"
                    },
                    "become": True
                })
            
            # Deploy SSH keys
            tasks.append({
                "name": f"Deploy SSH keys for {username}",
                "authorized_key": {
                    "user": username,
                    "state": "present",
                    "key": "{{ item }}"
                },
                "loop": ssh_keys,
                "become": True
            })
            
            # Set up SSH directory permissions
            tasks.append({
                "name": f"Set SSH directory permissions for {username}",
                "file": {
                    "path": f"/home/{username}/.ssh",
                    "state": "directory",
                    "mode": "0700",
                    "owner": username,
                    "group": username
                },
                "become": True
            })
            
            playbook = {
                "name": f"Deploy SSH keys for {username}",
                "hosts": "all",
                "gather_facts": True,
                "tasks": tasks
            }
            
            # Run the playbook
            result = await self.ansible_runner.run_playbook_dict(
                playbook=playbook,
                inventory=inventory
            )
            
            # Store authentication info in context if successful
            if result.get("success", False):
                for host in hosts.split(","):
                    host = host.strip()
                    await self.context_manager.update_device_authentication(
                        ip_address=host,
                        ssh_keys=ssh_keys,
                        ansible_user=username,
                        auth_method="ssh_key",
                        sudo_access=sudo_access
                    )
            
            return {
                "success": result.get("success", False),
                "deployed_to": hosts.split(","),
                "username": username,
                "keys_deployed": len(ssh_keys),
                "ansible_output": result.get("stdout", ""),
                "errors": result.get("stderr", "") if not result.get("success") else None,
                "context_updated": result.get("success", False)
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy SSH keys: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def setup_complete_auth(
        self,
        host: str,
        github_username: str,
        ansible_user: str = "ansible-admin",
        initial_auth: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Complete authentication setup for a new homelab server."""
        try:
            results = {
                "host": host,
                "github_username": github_username,
                "ansible_user": ansible_user,
                "steps": []
            }
            
            # Step 1: Fetch GitHub SSH keys
            step1 = await self.fetch_github_keys(github_username)
            results["steps"].append({
                "step": "fetch_github_keys",
                "success": step1["success"],
                "details": step1
            })
            
            if not step1["success"]:
                return {
                    "success": False,
                    "error": "Failed to fetch GitHub SSH keys",
                    "details": results
                }
            
            ssh_keys = step1["keys"]
            if not ssh_keys:
                return {
                    "success": False,
                    "error": f"No compatible SSH keys found for GitHub user {github_username}",
                    "details": results
                }
            
            # Step 2: Deploy SSH keys to server
            step2 = await self.deploy_ssh_keys(
                hosts=host,
                ssh_keys=ssh_keys,
                username=ansible_user,
                create_user=True,
                sudo_access=True,
                initial_auth=initial_auth
            )
            results["steps"].append({
                "step": "deploy_ssh_keys",
                "success": step2["success"],
                "details": step2
            })
            
            if not step2["success"]:
                return {
                    "success": False,
                    "error": "Failed to deploy SSH keys",
                    "details": results
                }
            
            # Step 3: Verify access
            step3 = await self.verify_access(host, ansible_user)
            results["steps"].append({
                "step": "verify_access",
                "success": step3["success"],
                "details": step3
            })
            
            # Step 4: Store complete authentication info in context
            if step3["success"]:
                await self.context_manager.update_device_authentication(
                    ip_address=host,
                    github_username=github_username,
                    ssh_keys=ssh_keys,
                    ansible_user=ansible_user,
                    auth_method="ssh_key",
                    sudo_access=True
                )
            
            return {
                "success": step3["success"],
                "message": f"Authentication setup complete for {host}",
                "github_keys_deployed": len(ssh_keys),
                "ansible_user": ansible_user,
                "github_username": github_username,
                "context_updated": step3["success"],
                "details": results
            }
            
        except Exception as e:
            logger.error(f"Failed complete auth setup: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def verify_access(self, host: str, username: str = "ansible-admin") -> Dict[str, Any]:
        """Verify SSH access and test authentication."""
        try:
            # Build inventory for verification
            inventory = {
                host: {
                    "ansible_host": host,
                    "ansible_user": username
                }
            }
            
            # Create verification playbook
            playbook = {
                "name": "Verify SSH access and authentication",
                "hosts": "all",
                "gather_facts": True,
                "tasks": [
                    {
                        "name": "Test basic connectivity",
                        "ping": {}
                    },
                    {
                        "name": "Test sudo access",
                        "command": "whoami",
                        "become": True,
                        "register": "sudo_test"
                    },
                    {
                        "name": "Get user info",
                        "user": {
                            "name": username,
                            "state": "present"
                        },
                        "register": "user_info"
                    }
                ]
            }
            
            result = await self.ansible_runner.run_playbook_dict(
                playbook=playbook,
                inventory=inventory
            )
            
            return {
                "success": result.get("success", False),
                "host": host,
                "username": username,
                "connectivity": "OK" if result.get("success") else "FAILED",
                "sudo_access": "OK" if result.get("success") else "UNKNOWN",
                "ansible_output": result.get("stdout", ""),
                "errors": result.get("stderr", "") if not result.get("success") else None
            }
            
        except Exception as e:
            logger.error(f"Failed to verify access: {e}")
            return {
                "success": False,
                "error": str(e),
                "host": host,
                "username": username
            }


async def handle_auth_setup_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle authentication setup tool execution."""
    try:
        manager = AuthSetupManager()
        
        if name == "fetch-github-ssh-keys":
            result = await manager.fetch_github_keys(
                username=arguments["username"],
                key_types=arguments.get("key_types", ["ssh-ed25519", "ssh-rsa"])
            )
            
        elif name == "deploy-ssh-keys":
            result = await manager.deploy_ssh_keys(
                hosts=arguments["hosts"],
                ssh_keys=arguments["ssh_keys"],
                username=arguments.get("username", "ansible-admin"),
                create_user=arguments.get("create_user", True),
                sudo_access=arguments.get("sudo_access", True),
                initial_auth=arguments.get("initial_auth")
            )
            
        elif name == "setup-homelab-auth":
            result = await manager.setup_complete_auth(
                host=arguments["host"],
                github_username=arguments["github_username"],
                ansible_user=arguments.get("ansible_user", "ansible-admin"),
                initial_auth=arguments["initial_auth"]
            )
            
        elif name == "verify-ssh-access":
            result = await manager.verify_access(
                host=arguments["host"],
                username=arguments.get("username", "ansible-admin")
            )
            
        elif name == "list-server-users":
            # Use ad-hoc command to list users
            runner = AnsibleRunner()
            inventory = {
                arguments["host"]: {
                    "ansible_host": arguments["host"],
                    "ansible_user": arguments.get("username", "ansible-admin")
                }
            }
            
            ansible_result = await runner.run_ad_hoc_command(
                hosts="all",
                module="shell",
                args="getent passwd | grep -E ':(100[0-9]|[1-9][0-9]{3,}):' | cut -d: -f1,3,5",
                inventory=inventory
            )
            
            result = {
                "success": ansible_result.get("success", False),
                "host": arguments["host"],
                "users_command_output": ansible_result.get("stdout", ""),
                "errors": ansible_result.get("stderr", "") if not ansible_result.get("success") else None
            }
            
        elif name == "get-authentication-context":
            # Get authentication context from homelab topology
            manager = AuthSetupManager()
            
            if arguments.get("host"):
                # Get specific host auth info
                auth_info = await manager.context_manager.get_device_authentication(arguments["host"])
                if auth_info:
                    result = {
                        "success": True,
                        "host": arguments["host"],
                        "authentication": {
                            "ansible_user": auth_info.ansible_user,
                            "github_username": auth_info.github_username,
                            "auth_method": auth_info.auth_method,
                            "sudo_access": auth_info.sudo_access,
                            "last_verified": auth_info.last_verified,
                            "setup_completed": auth_info.setup_completed,
                            "ssh_keys_count": len(auth_info.ssh_keys_deployed)
                        }
                    }
                else:
                    result = {
                        "success": False,
                        "error": f"No authentication information found for {arguments['host']}"
                    }
            else:
                # Get all authenticated devices
                auth_devices = await manager.context_manager.list_authenticated_devices()
                result = {
                    "success": True,
                    "authenticated_devices": auth_devices,
                    "total_devices": len(auth_devices)
                }
            
        elif name == "suggest-github-username":
            # Suggest GitHub username from context
            manager = AuthSetupManager()
            username = await manager.context_manager.get_github_username_from_context()
            
            if username:
                result = {
                    "success": True,
                    "suggestion": username,
                    "source": "existing_context",
                    "message": f"Found GitHub username '{username}' from previous authentication setup"
                }
            else:
                result = {
                    "success": False,
                    "suggestion": None,
                    "source": "user_input_required",
                    "message": "No GitHub username found in context. Please provide your GitHub username for SSH key setup."
                }
        
        elif name == "generate-mcp-ssh-key":
            # Generate MCP SSH key
            mcp_ssh = MCPSSHKeyManager()
            result = await mcp_ssh.generate_mcp_ssh_key(
                key_type=arguments.get("key_type", "ed25519"),
                key_comment=arguments.get("key_comment"),
                force_regenerate=arguments.get("force_regenerate", False)
            )
            
        elif name == "setup-homelab-auth-mcp":
            # Complete auth setup using MCP SSH key
            mcp_ssh = MCPSSHKeyManager()
            
            # Auto-generate key if requested and doesn't exist
            if arguments.get("auto_generate_key", True):
                key_info = await mcp_ssh.get_mcp_key_info()
                if not key_info.get("ready_for_deployment", False):
                    logger.info("Generating MCP SSH key automatically...")
                    gen_result = await mcp_ssh.generate_mcp_ssh_key()
                    if not gen_result.get("success"):
                        result = {
                            "success": False,
                            "error": "Failed to generate MCP SSH key",
                            "details": gen_result
                        }
                        return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            # Deploy MCP key to server
            deploy_result = await mcp_ssh.deploy_mcp_key_to_server(
                host=arguments["host"],
                initial_auth=arguments["initial_auth"],
                ansible_user=arguments.get("ansible_user", "ansible-admin")
            )
            
            if deploy_result.get("success"):
                # Test access
                test_result = await mcp_ssh.test_mcp_ssh_access(
                    host=arguments["host"],
                    user=arguments.get("ansible_user", "ansible-admin")
                )
                
                # Update context
                manager = AuthSetupManager()
                public_key = await mcp_ssh.get_mcp_public_key()
                await manager.context_manager.update_device_authentication(
                    ip_address=arguments["host"],
                    ssh_keys=[public_key] if public_key else [],
                    ansible_user=arguments.get("ansible_user", "ansible-admin"),
                    auth_method="mcp_ssh_key",
                    sudo_access=True
                )
                
                result = {
                    "success": True,
                    "message": f"MCP authentication setup complete for {arguments['host']}",
                    "deployment": deploy_result,
                    "access_test": test_result,
                    "context_updated": True,
                    "mcp_key_used": True
                }
            else:
                result = {
                    "success": False,
                    "error": "Failed to deploy MCP SSH key",
                    "details": deploy_result
                }
            
        elif name == "get-mcp-ssh-key-info":
            # Get MCP SSH key information
            mcp_ssh = MCPSSHKeyManager()
            result = await mcp_ssh.get_mcp_key_info()
            
        elif name == "test-mcp-ssh-access":
            # Test MCP SSH access
            mcp_ssh = MCPSSHKeyManager()
            result = await mcp_ssh.test_mcp_ssh_access(
                host=arguments["host"],
                user=arguments.get("user", "ansible-admin")
            )
            
        elif name == "setup-universal-auth":
            # Setup universal authentication for any provider
            universal_auth = UniversalAuthManager()
            
            # Extract provider-specific parameters
            provider_params = {}
            for key, value in arguments.items():
                if key not in ["provider_type", "endpoint", "auth_method"]:
                    if value is not None:  # Only include non-None values
                        provider_params[key] = value
            
            result = await universal_auth.setup_universal_auth(
                provider_type=arguments["provider_type"],
                endpoint=arguments["endpoint"],
                auth_method=arguments.get("auth_method", "auto"),
                **provider_params
            )
            
        elif name == "list-auth-configurations":
            # List all authentication configurations
            universal_auth = UniversalAuthManager()
            configs = await universal_auth.list_auth_configs()
            
            # Filter by provider type if specified
            provider_filter = arguments.get("provider_type")
            if provider_filter:
                configs = [c for c in configs if c.get("provider_type") == provider_filter]
            
            result = {
                "success": True,
                "configurations": configs,
                "total_count": len(configs),
                "filter_applied": provider_filter is not None
            }
            
        elif name == "get-auth-configuration":
            # Get specific authentication configuration
            universal_auth = UniversalAuthManager()
            auth_config = await universal_auth.get_auth_config(
                provider_type=arguments["provider_type"],
                endpoint=arguments["endpoint"]
            )
            
            if auth_config:
                # Convert to dict and remove sensitive data
                config_dict = {
                    "provider_type": auth_config.provider_type,
                    "auth_method": auth_config.auth_method,
                    "endpoint": auth_config.endpoint,
                    "ssh_user": auth_config.ssh_user,
                    "ssh_port": auth_config.ssh_port,
                    "username": auth_config.username,
                    "domain": auth_config.domain,
                    "created_at": auth_config.created_at,
                    "last_verified": auth_config.last_verified,
                    "expires_at": auth_config.expires_at,
                    "notes": auth_config.notes,
                    "has_api_token": bool(auth_config.api_token),
                    "has_ssh_key": bool(auth_config.ssh_key_path),
                    "has_certificates": bool(auth_config.cert_path)
                }
                
                result = {
                    "success": True,
                    "configuration": config_dict
                }
            else:
                result = {
                    "success": False,
                    "error": f"No authentication configuration found for {arguments['provider_type']} at {arguments['endpoint']}"
                }
            
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
        
    except Exception as e:
        logger.error(f"Auth setup tool error: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": str(e),
                "tool": name,
                "arguments": arguments
            }, indent=2)
        )]