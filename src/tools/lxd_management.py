"""
LXD container management tools with automatic installation support.
Handles LXD installation, configuration, and container lifecycle.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import yaml

from ..utils.lxd_api import LXDAPIClient
from ..utils.ansible_runner import AnsibleRunner
from ..security.credential_manager import get_credential_manager
from .lxd_discovery import get_lxd_discovery_tools

logger = logging.getLogger(__name__)


class LXDManagementTools:
    """MCP tools for managing LXD containers with automatic setup."""
    
    def __init__(self):
        self.credential_manager = get_credential_manager()
        self.discovery_tools = get_lxd_discovery_tools()
        self.ansible_runner = AnsibleRunner()
        
    async def check_lxd_installed(
        self,
        host: str,
        ssh_user: str = "pi",
        ssh_port: int = 22
    ) -> Dict[str, Any]:
        """
        Check if LXD is installed on target host.
        
        Args:
            host: Target hostname or IP
            ssh_user: SSH username
            ssh_port: SSH port
            
        Returns:
            Installation status and version info
        """
        try:
            # Create simple Ansible playbook to check LXD
            playbook = {
                "name": "Check LXD installation",
                "hosts": host,
                "gather_facts": True,
                "tasks": [
                    {
                        "name": "Check if LXD is installed via snap",
                        "command": "snap list lxd",
                        "register": "snap_lxd",
                        "ignore_errors": True
                    },
                    {
                        "name": "Check if LXD is installed via apt",
                        "command": "dpkg -l | grep lxd",
                        "register": "apt_lxd",
                        "ignore_errors": True
                    },
                    {
                        "name": "Get LXD version",
                        "command": "lxd version",
                        "register": "lxd_version",
                        "when": "snap_lxd.rc == 0 or apt_lxd.rc == 0",
                        "ignore_errors": True
                    },
                    {
                        "name": "Check LXD init status",
                        "command": "lxc list",
                        "register": "lxd_init_check",
                        "ignore_errors": True
                    }
                ]
            }
            
            # Run playbook
            result = await self.ansible_runner.run_playbook_dict(
                playbook,
                inventory={host: {"ansible_user": ssh_user, "ansible_port": ssh_port}}
            )
            
            # Parse results
            installed = False
            version = None
            initialized = False
            install_method = None
            
            if result.get("success"):
                stats = result.get("stats", {}).get(host, {})
                
                # Check if installed
                if stats.get("snap_lxd", {}).get("rc") == 0:
                    installed = True
                    install_method = "snap"
                elif stats.get("apt_lxd", {}).get("rc") == 0:
                    installed = True
                    install_method = "apt"
                    
                # Get version
                if installed and stats.get("lxd_version", {}).get("rc") == 0:
                    version = stats.get("lxd_version", {}).get("stdout", "").strip()
                    
                # Check if initialized
                if stats.get("lxd_init_check", {}).get("rc") == 0:
                    initialized = True
                    
            return {
                "installed": installed,
                "version": version,
                "initialized": initialized,
                "install_method": install_method,
                "host": host,
                "check_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to check LXD installation: {e}")
            return {
                "installed": False,
                "error": str(e),
                "host": host
            }
            
    async def install_lxd(
        self,
        host: str,
        ssh_user: str = "pi",
        ssh_port: int = 22,
        storage_backend: str = "dir",
        storage_size: str = "20GB",
        network_address: str = "10.0.0.1/24"
    ) -> Dict[str, Any]:
        """
        Install and configure LXD on target host.
        
        Args:
            host: Target hostname or IP
            ssh_user: SSH username
            ssh_port: SSH port
            storage_backend: Storage backend (dir, btrfs, zfs)
            storage_size: Storage pool size
            network_address: LXD bridge network address
            
        Returns:
            Installation result
        """
        try:
            # First check if already installed
            check_result = await self.check_lxd_installed(host, ssh_user, ssh_port)
            
            if check_result.get("installed") and check_result.get("initialized"):
                return {
                    "success": True,
                    "message": "LXD is already installed and initialized",
                    "version": check_result.get("version")
                }
                
            # Create installation playbook
            tasks = []
            
            # Install LXD if not present
            if not check_result.get("installed"):
                tasks.extend([
                    {
                        "name": "Update apt cache",
                        "apt": {
                            "update_cache": True
                        },
                        "become": True
                    },
                    {
                        "name": "Install snapd",
                        "apt": {
                            "name": "snapd",
                            "state": "present"
                        },
                        "become": True
                    },
                    {
                        "name": "Install LXD via snap",
                        "snap": {
                            "name": "lxd",
                            "state": "present"
                        },
                        "become": True
                    },
                    {
                        "name": "Add user to lxd group",
                        "user": {
                            "name": ssh_user,
                            "groups": "lxd",
                            "append": True
                        },
                        "become": True
                    }
                ])
                
            # Initialize LXD if needed
            if not check_result.get("initialized"):
                # Create preseed file for LXD init
                preseed = {
                    "config": {},
                    "networks": [
                        {
                            "config": {
                                "ipv4.address": network_address,
                                "ipv4.nat": "true"
                            },
                            "description": "",
                            "name": "lxdbr0",
                            "type": "bridge"
                        }
                    ],
                    "storage_pools": [
                        {
                            "config": {
                                "size": storage_size
                            },
                            "description": "",
                            "name": "default",
                            "driver": storage_backend
                        }
                    ],
                    "profiles": [
                        {
                            "config": {},
                            "description": "",
                            "devices": {
                                "eth0": {
                                    "name": "eth0",
                                    "network": "lxdbr0",
                                    "type": "nic"
                                },
                                "root": {
                                    "path": "/",
                                    "pool": "default",
                                    "type": "disk"
                                }
                            },
                            "name": "default"
                        }
                    ]
                }
                
                tasks.extend([
                    {
                        "name": "Create LXD preseed file",
                        "copy": {
                            "content": yaml.dump(preseed),
                            "dest": "/tmp/lxd-preseed.yaml"
                        }
                    },
                    {
                        "name": "Initialize LXD with preseed",
                        "shell": "cat /tmp/lxd-preseed.yaml | lxd init --preseed",
                        "become": True
                    },
                    {
                        "name": "Remove preseed file",
                        "file": {
                            "path": "/tmp/lxd-preseed.yaml",
                            "state": "absent"
                        }
                    },
                    {
                        "name": "Enable LXD remote access",
                        "command": "lxc config set core.https_address [::]",
                        "become": True
                    },
                    {
                        "name": "Set LXD password for remote access",
                        "expect": {
                            "command": "lxc config set core.trust_password changeme",
                            "responses": {
                                "password": "changeme"
                            }
                        },
                        "become": True
                    }
                ])
                
            # Build and run playbook
            playbook = {
                "name": "Install and configure LXD",
                "hosts": host,
                "gather_facts": True,
                "tasks": tasks
            }
            
            result = await self.ansible_runner.run_playbook_dict(
                playbook,
                inventory={host: {"ansible_user": ssh_user, "ansible_port": ssh_port}}
            )
            
            if result.get("success"):
                # Store LXD credentials
                await self.credential_manager.store_credentials("lxd", {
                    "host": host,
                    "port": 8443,
                    "ssh_user": ssh_user,
                    "ssh_port": ssh_port,
                    "connection_method": "ssh",
                    "trust_password": "changeme"  # User should change this
                })
                
                return {
                    "success": True,
                    "message": "LXD installed and initialized successfully",
                    "host": host,
                    "network": network_address,
                    "storage": f"{storage_backend} ({storage_size})",
                    "note": "Please change the trust password from 'changeme' for security"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Installation failed"),
                    "details": result
                }
                
        except Exception as e:
            logger.error(f"Failed to install LXD: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def create_container(
        self,
        name: str,
        image: str = "ubuntu:22.04",
        cpu_limit: Optional[str] = None,
        memory_limit: Optional[str] = None,
        disk_limit: Optional[str] = None,
        profiles: Optional[List[str]] = None,
        autostart: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new LXD container.
        
        Args:
            name: Container name
            image: Container image (e.g., ubuntu:22.04)
            cpu_limit: CPU limit (e.g., "2" for 2 cores)
            memory_limit: Memory limit (e.g., "2GB")
            disk_limit: Disk limit (e.g., "10GB")
            profiles: List of profiles to apply
            autostart: Start container after creation
            
        Returns:
            Creation result with container details
        """
        try:
            # Get LXD client
            client = await self.discovery_tools._get_client()
            
            # Build container config
            config = {}
            if cpu_limit:
                config["limits.cpu"] = cpu_limit
            if memory_limit:
                config["limits.memory"] = memory_limit
                
            # Build devices config
            devices = {}
            if disk_limit:
                devices["root"] = {
                    "type": "disk",
                    "path": "/",
                    "pool": "default",
                    "size": disk_limit
                }
                
            # Create container
            result = await client.create_container(
                name=name,
                image=image,
                profiles=profiles or ["default"],
                config=config,
                devices=devices
            )
            
            # Start container if requested
            if autostart:
                await client.start_container(name)
                
                # Wait for IP address
                ip_address = None
                for _ in range(30):  # Wait up to 30 seconds
                    await asyncio.sleep(1)
                    state = await client.get_container_state(name)
                    
                    for iface_name, iface_data in state.get("network", {}).items():
                        for addr in iface_data.get("addresses", []):
                            if addr.get("family") == "inet" and not addr["address"].startswith("127."):
                                ip_address = addr["address"]
                                break
                        if ip_address:
                            break
                            
                    if ip_address:
                        break
                        
            # Get final container details
            details = await self.discovery_tools.get_container_details(name)
            
            return {
                "success": True,
                "container": {
                    "name": name,
                    "image": image,
                    "status": details.get("status"),
                    "ip_address": ip_address,
                    "config": config,
                    "profiles": profiles or ["default"]
                },
                "message": f"Container '{name}' created successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to create container: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def manage_container(
        self,
        name: str,
        action: str
    ) -> Dict[str, Any]:
        """
        Manage container lifecycle (start, stop, restart, delete).
        
        Args:
            name: Container name
            action: Action to perform (start, stop, restart, delete)
            
        Returns:
            Action result
        """
        try:
            client = await self.discovery_tools._get_client()
            
            if action == "start":
                await client.start_container(name)
                message = f"Container '{name}' started"
                
            elif action == "stop":
                await client.stop_container(name)
                message = f"Container '{name}' stopped"
                
            elif action == "restart":
                await client.stop_container(name)
                await asyncio.sleep(1)
                await client.start_container(name)
                message = f"Container '{name}' restarted"
                
            elif action == "delete":
                # Stop first if running
                try:
                    await client.stop_container(name, force=True)
                    await asyncio.sleep(1)
                except Exception:
                    pass  # Already stopped
                    
                await client.delete_container(name)
                message = f"Container '{name}' deleted"
                
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
                
            return {
                "success": True,
                "message": message,
                "container": name,
                "action": action
            }
            
        except Exception as e:
            logger.error(f"Failed to {action} container: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def install_service_in_container(
        self,
        container_name: str,
        service: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Install a service inside an LXD container.
        
        Args:
            container_name: Target container name
            service: Service to install (nginx, mysql, etc.)
            config: Optional service configuration
            
        Returns:
            Installation result
        """
        try:
            # Get container details
            details = await self.discovery_tools.get_container_details(container_name)
            
            if details.get("status") != "Running":
                return {
                    "success": False,
                    "error": f"Container '{container_name}' is not running"
                }
                
            # Get container IP
            client = await self.discovery_tools._get_client()
            state = await client.get_container_state(container_name)
            
            ip_address = None
            for iface_name, iface_data in state.get("network", {}).items():
                for addr in iface_data.get("addresses", []):
                    if addr.get("family") == "inet" and not addr["address"].startswith("127."):
                        ip_address = addr["address"]
                        break
                if ip_address:
                    break
                    
            if not ip_address:
                return {
                    "success": False,
                    "error": "Could not determine container IP address"
                }
                
            # Build service installation playbook
            service_tasks = {
                "nginx": [
                    {
                        "name": "Install nginx",
                        "apt": {
                            "name": "nginx",
                            "state": "present"
                        }
                    },
                    {
                        "name": "Start nginx",
                        "service": {
                            "name": "nginx",
                            "state": "started",
                            "enabled": True
                        }
                    }
                ],
                "mysql": [
                    {
                        "name": "Install MySQL",
                        "apt": {
                            "name": ["mysql-server", "python3-pymysql"],
                            "state": "present"
                        }
                    },
                    {
                        "name": "Start MySQL",
                        "service": {
                            "name": "mysql",
                            "state": "started",
                            "enabled": True
                        }
                    }
                ],
                "docker": [
                    {
                        "name": "Install Docker dependencies",
                        "apt": {
                            "name": ["apt-transport-https", "ca-certificates", "curl", "software-properties-common"],
                            "state": "present"
                        }
                    },
                    {
                        "name": "Add Docker GPG key",
                        "apt_key": {
                            "url": "https://download.docker.com/linux/ubuntu/gpg",
                            "state": "present"
                        }
                    },
                    {
                        "name": "Add Docker repository",
                        "apt_repository": {
                            "repo": "deb [arch=arm64] https://download.docker.com/linux/ubuntu {{ ansible_distribution_release }} stable",
                            "state": "present"
                        }
                    },
                    {
                        "name": "Install Docker",
                        "apt": {
                            "name": "docker-ce",
                            "state": "present",
                            "update_cache": True
                        }
                    },
                    {
                        "name": "Start Docker",
                        "service": {
                            "name": "docker",
                            "state": "started",
                            "enabled": True
                        }
                    }
                ]
            }
            
            tasks = service_tasks.get(service.lower())
            if not tasks:
                return {
                    "success": False,
                    "error": f"Unknown service: {service}"
                }
                
            # Add common tasks
            all_tasks = [
                {
                    "name": "Update apt cache",
                    "apt": {
                        "update_cache": True
                    }
                }
            ] + tasks
            
            # Build playbook
            playbook = {
                "name": f"Install {service} in container",
                "hosts": ip_address,
                "gather_facts": True,
                "become": True,
                "tasks": all_tasks
            }
            
            # Run playbook
            result = await self.ansible_runner.run_playbook_dict(
                playbook,
                inventory={ip_address: {"ansible_user": "ubuntu"}}
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "message": f"{service} installed successfully in container '{container_name}'",
                    "container": container_name,
                    "service": service,
                    "ip_address": ip_address
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Installation failed"),
                    "details": result
                }
                
        except Exception as e:
            logger.error(f"Failed to install service: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Create singleton instance
_lxd_management_tools = None


def get_lxd_management_tools() -> LXDManagementTools:
    """Get singleton instance of LXD management tools."""
    global _lxd_management_tools
    if _lxd_management_tools is None:
        _lxd_management_tools = LXDManagementTools()
    return _lxd_management_tools