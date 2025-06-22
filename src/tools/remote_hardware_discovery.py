"""
Remote Hardware Discovery Tools
Discovers hardware on remote systems and updates homelab context.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import asdict

from mcp.types import Tool, TextContent

from ..utils.homelab_context import HomelabContextManager, HomelabDevice, DeviceCapabilities
from ..utils.ansible_runner import AnsibleRunner
from .system_hardware_discovery import SystemHardware
from .mcp_ssh_manager import MCPSSHKeyManager

logger = logging.getLogger(__name__)


class RemoteHardwareDiscovery:
    """Discovers hardware on remote systems and updates homelab context."""
    
    def __init__(self):
        self.context_manager = HomelabContextManager()
        self.ansible_runner = AnsibleRunner()
        self.ssh_manager = MCPSSHKeyManager()
    
    async def discover_remote_hardware(
        self, 
        ip_address: str,
        ssh_user: Optional[str] = None,
        ssh_password: Optional[str] = None,
        use_existing_auth: bool = True
    ) -> Dict[str, Any]:
        """
        Discover hardware on a remote system and update homelab context.
        
        Args:
            ip_address: Target system IP address
            ssh_user: SSH username (will prompt if needed)
            ssh_password: SSH password (will prompt if needed)
            use_existing_auth: Try existing SSH keys first
            
        Returns:
            Discovery results with hardware info and context update status
        """
        
        result = {
            "ip_address": ip_address,
            "discovery_status": "started",
            "hardware": None,
            "context_updated": False,
            "authentication": None,
            "errors": []
        }
        
        try:
            # Step 1: Check if device exists in context
            existing_device = await self.context_manager.get_device(ip_address)
            if existing_device:
                logger.info(f"Device {ip_address} already in context, updating...")
            
            # Step 2: Test SSH connectivity
            ssh_access = await self._test_ssh_access(ip_address, ssh_user, use_existing_auth)
            
            if not ssh_access["success"]:
                # SSH failed, need to set up authentication
                result["authentication"] = await self._setup_ssh_authentication(
                    ip_address, ssh_user, ssh_password
                )
                
                if not result["authentication"]["success"]:
                    result["discovery_status"] = "auth_failed"
                    result["errors"].append("Failed to establish SSH access")
                    return result
                
                # Update SSH user for discovery
                ssh_user = result["authentication"]["ssh_user"]
            else:
                result["authentication"] = {
                    "success": True,
                    "method": "existing_keys",
                    "ssh_user": ssh_access.get("ssh_user", ssh_user)
                }
                ssh_user = ssh_access.get("ssh_user", ssh_user)
            
            # Step 3: Run hardware discovery via Ansible
            hardware_data = await self._discover_hardware_via_ansible(ip_address, ssh_user)
            
            if hardware_data["success"]:
                result["hardware"] = hardware_data["hardware"]
                result["discovery_status"] = "completed"
                
                # Step 4: Update homelab context
                context_updated = await self._update_homelab_context(
                    ip_address, 
                    hardware_data["hardware"],
                    ssh_user
                )
                result["context_updated"] = context_updated
            else:
                result["discovery_status"] = "discovery_failed"
                result["errors"].append(hardware_data.get("error", "Hardware discovery failed"))
        
        except Exception as e:
            logger.error(f"Remote hardware discovery failed for {ip_address}: {e}")
            result["discovery_status"] = "error"
            result["errors"].append(str(e))
        
        return result
    
    async def _test_ssh_access(
        self, 
        ip_address: str, 
        ssh_user: Optional[str],
        use_existing_auth: bool
    ) -> Dict[str, Any]:
        """Test SSH access to remote system."""
        
        if not use_existing_auth:
            return {"success": False, "reason": "Existing auth disabled"}
        
        # Try common default users if none provided
        users_to_try = []
        if ssh_user:
            users_to_try.append(ssh_user)
        else:
            # Try common defaults
            users_to_try.extend(["ansible-admin", "ubuntu", "debian", "root"])
        
        for user in users_to_try:
            try:
                # Use MCP SSH manager to test access
                test_result = await self.ssh_manager.test_mcp_ssh_access(ip_address, user)
                if test_result.get("success"):
                    return {
                        "success": True,
                        "ssh_user": user,
                        "method": "ssh_key"
                    }
            except Exception as e:
                logger.debug(f"SSH test failed for {user}@{ip_address}: {e}")
        
        return {"success": False, "reason": "No working SSH access found"}
    
    async def _setup_ssh_authentication(
        self,
        ip_address: str,
        ssh_user: Optional[str],
        ssh_password: Optional[str]
    ) -> Dict[str, Any]:
        """Set up SSH authentication interactively."""
        
        # This would normally interact with the user
        # For now, we'll return a structure showing what's needed
        
        setup_result = {
            "success": False,
            "method": None,
            "ssh_user": ssh_user,
            "steps_needed": []
        }
        
        if not ssh_user:
            setup_result["steps_needed"].append({
                "type": "input",
                "prompt": f"Enter SSH username for {ip_address}",
                "field": "ssh_user",
                "suggestions": ["root", "ubuntu", "debian", "admin"]
            })
        
        if not ssh_password:
            setup_result["steps_needed"].append({
                "type": "password",
                "prompt": f"Enter SSH password for {ssh_user or 'user'}@{ip_address}",
                "field": "ssh_password"
            })
        
        # If we have credentials, try to deploy SSH key
        if ssh_user and ssh_password:
            try:
                deploy_result = await self.ssh_manager.deploy_mcp_key_to_server(
                    host=ip_address,
                    initial_auth={
                        "method": "password",
                        "username": ssh_user,
                        "password": ssh_password
                    },
                    ansible_user=ssh_user
                )
                
                if deploy_result.get("success"):
                    setup_result["success"] = True
                    setup_result["method"] = "deployed_ssh_key"
                    setup_result["ssh_user"] = ssh_user
                else:
                    setup_result["error"] = deploy_result.get("error", "Key deployment failed")
                    
            except Exception as e:
                setup_result["error"] = str(e)
        
        return setup_result
    
    async def _discover_hardware_via_ansible(
        self,
        ip_address: str,
        ssh_user: str
    ) -> Dict[str, Any]:
        """Run hardware discovery on remote system via Ansible."""
        
        try:
            # Create Ansible playbook for hardware discovery
            discovery_playbook = {
                "name": "Discover System Hardware",
                "hosts": "all",
                "gather_facts": True,
                "tasks": [
                    {
                        "name": "Gather hardware facts",
                        "setup": {
                            "gather_subset": [
                                "all",
                                "hardware",
                                "network",
                                "virtual"
                            ]
                        }
                    },
                    {
                        "name": "Get CPU info",
                        "command": "lscpu -J",
                        "register": "lscpu_output",
                        "ignore_errors": True
                    },
                    {
                        "name": "Get block devices", 
                        "command": "lsblk -J -o NAME,SIZE,TYPE,MODEL,FSTYPE,MOUNTPOINT",
                        "register": "lsblk_output",
                        "ignore_errors": True
                    },
                    {
                        "name": "Get PCI devices",
                        "command": "lspci",
                        "register": "lspci_output",
                        "ignore_errors": True
                    },
                    {
                        "name": "Get memory info",
                        "command": "cat /proc/meminfo",
                        "register": "meminfo_output",
                        "ignore_errors": True
                    },
                    {
                        "name": "Return hardware info",
                        "set_fact": {
                            "hardware_info": {
                                "ansible_facts": "{{ ansible_facts }}",
                                "lscpu": "{{ lscpu_output.stdout | default('') }}",
                                "lsblk": "{{ lsblk_output.stdout | default('') }}",
                                "lspci": "{{ lspci_output.stdout | default('') }}",
                                "meminfo": "{{ meminfo_output.stdout | default('') }}"
                            }
                        }
                    },
                    {
                        "name": "Display hardware info",
                        "debug": {
                            "var": "hardware_info"
                        }
                    }
                ]
            }
            
            # Run the playbook
            inventory = {
                ip_address: {
                    "ansible_host": ip_address,
                    "ansible_user": ssh_user,
                    "ansible_ssh_private_key_file": str(self.ssh_manager.private_key_path)
                }
            }
            
            result = await self.ansible_runner.run_playbook_dict(
                playbook=discovery_playbook,
                inventory=inventory,
                execution_name=f"hardware-discovery-{ip_address}",
                target_hosts=[ip_address]
            )
            
            if result["success"]:
                # Parse the output to extract hardware info
                hardware = await self._parse_ansible_hardware_output(result["stdout"])
                return {
                    "success": True,
                    "hardware": hardware
                }
            else:
                return {
                    "success": False,
                    "error": "Ansible playbook execution failed",
                    "details": result.get("stderr", "")
                }
                
        except Exception as e:
            logger.error(f"Hardware discovery failed via Ansible: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _parse_ansible_hardware_output(self, ansible_output: str) -> SystemHardware:
        """Parse Ansible output to extract hardware information."""
        
        hardware = SystemHardware()
        
        try:
            # This is a simplified parser - in reality we'd parse the JSON output
            # For now, extract basic info from ansible facts
            
            import re
            
            # Extract hostname
            hostname_match = re.search(r'"ansible_hostname":\s*"([^"]+)"', ansible_output)
            if hostname_match:
                hardware.hostname = hostname_match.group(1)
            
            # Extract distribution
            dist_match = re.search(r'"ansible_distribution":\s*"([^"]+)"', ansible_output)
            version_match = re.search(r'"ansible_distribution_version":\s*"([^"]+)"', ansible_output)
            if dist_match:
                hardware.distribution = dist_match.group(1)
                if version_match:
                    hardware.distribution += f" {version_match.group(1)}"
            
            # Extract kernel
            kernel_match = re.search(r'"ansible_kernel":\s*"([^"]+)"', ansible_output)
            if kernel_match:
                hardware.kernel = kernel_match.group(1)
            
            # Extract CPU info
            cpu_count_match = re.search(r'"ansible_processor_count":\s*(\d+)', ansible_output)
            cpu_cores_match = re.search(r'"ansible_processor_cores":\s*(\d+)', ansible_output)
            if cpu_count_match and cpu_cores_match:
                from .system_hardware_discovery import SystemCPU
                hardware.cpu = SystemCPU()
                hardware.cpu.cores = int(cpu_cores_match.group(1))
                hardware.cpu.threads = int(cpu_count_match.group(1))
            
            # Extract memory
            mem_total_match = re.search(r'"ansible_memtotal_mb":\s*(\d+)', ansible_output)
            if mem_total_match:
                from .system_hardware_discovery import SystemMemory
                hardware.memory = SystemMemory()
                hardware.memory.total_gb = int(mem_total_match.group(1)) / 1024
            
        except Exception as e:
            logger.warning(f"Failed to parse Ansible hardware output: {e}")
        
        return hardware
    
    async def _update_homelab_context(
        self,
        ip_address: str,
        hardware: SystemHardware,
        ssh_user: str
    ) -> bool:
        """Update homelab context with discovered hardware."""
        
        try:
            # Create DeviceCapabilities from hardware info
            capabilities = DeviceCapabilities(
                cpu_cores=hardware.cpu.cores if hardware.cpu else 0,
                memory_gb=int(hardware.memory.total_gb) if hardware.memory else 0,
                storage_gb=sum(s.size_gb for s in hardware.storage) if hardware.storage else 0,
                network_interfaces=[n.interface for n in hardware.network] if hardware.network else [],
                gpu={
                    "count": len(hardware.gpus) if hardware.gpus else 0,
                    "models": [g.model for g in hardware.gpus] if hardware.gpus else []
                } if hardware.gpus else None
            )
            
            # Determine device role based on capabilities
            role = await self._determine_device_role(capabilities, hardware)
            
            # Create or update device in context
            device = HomelabDevice(
                ip_address=ip_address,
                hostname=hardware.hostname or f"unknown-{ip_address.replace('.', '-')}",
                role=role,
                device_type=await self._determine_device_type(hardware),
                exclude_from_homelab=False,
                capabilities=capabilities,
                services=[],  # Will be discovered separately
                notes=f"Auto-discovered on {hardware.distribution or 'Unknown OS'}"
            )
            
            # Add authentication info
            from ..utils.homelab_context import AuthenticationInfo
            device.authentication = AuthenticationInfo(
                ansible_user=ssh_user,
                ssh_keys_deployed=[str(self.ssh_manager.public_key_path)],
                auth_method="ssh_key",
                sudo_access=True,  # Assumed if we could run discovery
                setup_completed=True
            )
            
            # Save to context
            success = await self.context_manager.add_device(device)
            
            if success:
                logger.info(f"Updated homelab context for {ip_address}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update homelab context: {e}")
            return False
    
    async def _determine_device_role(
        self,
        capabilities: DeviceCapabilities,
        hardware: SystemHardware
    ) -> str:
        """Determine device role based on capabilities."""
        
        # High-performance server
        if capabilities.cpu_cores >= 16 and capabilities.memory_gb >= 32:
            return "infrastructure_host"
        
        # GPU server
        if capabilities.gpu and capabilities.gpu.get("count", 0) > 0:
            return "ai_compute_host"
        
        # Mid-range server
        if capabilities.cpu_cores >= 4 and capabilities.memory_gb >= 8:
            return "service_host"
        
        # Low-power device (Pi, NUC, etc)
        if capabilities.cpu_cores <= 4 and capabilities.memory_gb <= 8:
            return "edge_device"
        
        # Storage server
        if capabilities.storage_gb >= 1000:  # 1TB+
            return "storage_device"
        
        return "unknown"
    
    async def _determine_device_type(self, hardware: SystemHardware) -> str:
        """Determine device type from hardware info."""
        
        if "raspberry" in hardware.hostname.lower() or "raspbian" in hardware.distribution.lower():
            return "raspberry_pi"
        
        if hardware.cpu and "xeon" in hardware.cpu.model.lower():
            return "server"
        
        if hardware.distribution and "proxmox" in hardware.distribution.lower():
            return "proxmox_host"
        
        if hardware.distribution and any(vm in hardware.distribution.lower() for vm in ["vmware", "esxi"]):
            return "vmware_host"
        
        return "bare_metal_server"


# Initialize discovery instance
remote_discovery = RemoteHardwareDiscovery()


def register_remote_hardware_tools(server):
    """Register remote hardware discovery tools with the MCP server."""
    
    @server.tool()
    async def discover_remote_system(
        ip_address: str,
        ssh_user: Optional[str] = None,
        update_context: bool = True
    ) -> List[TextContent]:
        """Discover hardware on a remote system and optionally update homelab context.
        
        Args:
            ip_address: IP address of the remote system
            ssh_user: SSH username (optional, will try common defaults)
            update_context: Whether to update homelab context (default: true)
        """
        
        result = await remote_discovery.discover_remote_hardware(
            ip_address=ip_address,
            ssh_user=ssh_user,
            use_existing_auth=True
        )
        
        output = [f"🔍 **Remote System Discovery: {ip_address}**\n"]
        
        # Authentication status
        if result["authentication"]:
            auth = result["authentication"]
            if auth["success"]:
                output.append(f"✅ Authentication: {auth['method']} as {auth.get('ssh_user', 'unknown')}")
            else:
                output.append("❌ Authentication failed")
                if auth.get("steps_needed"):
                    output.append("\n**Authentication Required:**")
                    for step in auth["steps_needed"]:
                        output.append(f"- {step['prompt']}")
                return [TextContent(type="text", text="\n".join(output))]
        
        # Hardware discovery results
        if result["hardware"]:
            hw = result["hardware"]
            output.append(f"\n**System Information:**")
            output.append(f"- Hostname: {hw.hostname}")
            output.append(f"- OS: {hw.distribution}")
            output.append(f"- Kernel: {hw.kernel}")
            
            if hw.cpu:
                output.append(f"\n**CPU:**")
                output.append(f"- Model: {hw.cpu.model}")
                output.append(f"- Cores: {hw.cpu.cores}, Threads: {hw.cpu.threads}")
            
            if hw.memory:
                output.append(f"\n**Memory:**")
                output.append(f"- Total: {hw.memory.total_gb:.1f} GB")
            
            if hw.storage:
                output.append(f"\n**Storage:**")
                total_storage = sum(s.size_gb for s in hw.storage)
                output.append(f"- Total: {total_storage:.1f} GB across {len(hw.storage)} devices")
            
            if hw.gpus:
                output.append(f"\n**GPUs:**")
                for gpu in hw.gpus:
                    output.append(f"- {gpu.model}")
        
        # Context update status
        if update_context and result["context_updated"]:
            output.append(f"\n✅ Homelab context updated successfully")
        elif update_context and not result["context_updated"]:
            output.append(f"\n❌ Failed to update homelab context")
        
        # Errors
        if result["errors"]:
            output.append(f"\n**Errors:**")
            for error in result["errors"]:
                output.append(f"- {error}")
        
        return [TextContent(type="text", text="\n".join(output))]
    
    @server.tool()
    async def setup_remote_ssh_access(
        ip_address: str,
        ssh_user: str,
        ssh_password: str
    ) -> List[TextContent]:
        """Set up SSH access to a remote system by deploying MCP SSH keys.
        
        Args:
            ip_address: IP address of the remote system
            ssh_user: SSH username
            ssh_password: SSH password for initial authentication
        """
        
        output = [f"🔐 **Setting up SSH access to {ip_address}**\n"]
        
        try:
            # Deploy SSH key
            deploy_result = await remote_discovery.ssh_manager.deploy_mcp_key_to_server(
                host=ip_address,
                initial_auth={
                    "method": "password",
                    "username": ssh_user,
                    "password": ssh_password
                },
                ansible_user=ssh_user
            )
            
            if deploy_result.get("success"):
                output.append(f"✅ SSH key deployed successfully")
                output.append(f"- User: {ssh_user}")
                output.append(f"- Key: {deploy_result.get('key_deployed', 'MCP SSH key')}")
                
                # Test the new access
                test_result = await remote_discovery.ssh_manager.test_mcp_ssh_access(
                    ip_address, ssh_user
                )
                
                if test_result.get("success"):
                    output.append(f"\n✅ SSH access verified")
                    output.append("\nYou can now use `discover_remote_system` to scan the hardware.")
                else:
                    output.append(f"\n⚠️ SSH key deployed but access test failed")
            else:
                output.append(f"❌ Failed to deploy SSH key")
                output.append(f"Error: {deploy_result.get('error', 'Unknown error')}")
                
        except Exception as e:
            output.append(f"❌ Error: {str(e)}")
        
        return [TextContent(type="text", text="\n".join(output))]


# Tool definitions
REMOTE_HARDWARE_TOOLS = [
    Tool(
        name="discover_remote_system",
        description="Get detailed hardware information (CPU, memory, storage, GPU) from a remote system via SSH - use this for checking server hardware specs",
        inputSchema={
            "type": "object",
            "properties": {
                "ip_address": {
                    "type": "string",
                    "description": "IP address of the remote system"
                },
                "ssh_user": {
                    "type": "string",
                    "description": "SSH username (optional, will try common defaults)"
                },
                "update_context": {
                    "type": "boolean",
                    "description": "Whether to update homelab context",
                    "default": True
                }
            },
            "required": ["ip_address"]
        }
    ),
    Tool(
        name="setup_remote_ssh_access",
        description="Set up SSH access to a remote system by deploying MCP SSH keys",
        inputSchema={
            "type": "object",
            "properties": {
                "ip_address": {
                    "type": "string",
                    "description": "IP address of the remote system"
                },
                "ssh_user": {
                    "type": "string",
                    "description": "SSH username"
                },
                "ssh_password": {
                    "type": "string",
                    "description": "SSH password for initial authentication"
                }
            },
            "required": ["ip_address", "ssh_user", "ssh_password"]
        }
    )
]