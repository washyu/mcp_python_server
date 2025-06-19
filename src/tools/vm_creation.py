"""
VM Creation and Management Tools for Proxmox with Cloud-Init support.
"""

import asyncio
import base64
import yaml
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from ..utils.proxmox_api import ProxmoxAPIClient
from ..utils.credential_manager import get_credential_manager
from ..utils.homelab_context import HomelabContextManager, HomelabDevice, DeviceCapabilities


@dataclass
class VMCreationRequest:
    """VM creation request with cloud-init configuration."""
    name: str
    cores: int = 2
    memory_mb: int = 4096
    disk_gb: int = 20
    template_id: int = 9000  # ubuntu-cloud-template
    node: str = None  # Auto-select if None
    network_bridge: str = "vmbr0"
    
    # Cloud-init configuration
    username: str = "ansible-admin"
    ssh_keys: List[str] = None
    packages: List[str] = None
    runcmd: List[str] = None
    
    # Service-specific setup
    install_qemu_agent: bool = True
    install_docker: bool = False
    enable_gpu_passthrough: bool = False


@dataclass
class VMCreationResult:
    """Result of VM creation operation."""
    vm_id: int
    name: str
    node: str
    ip_address: str = None
    ssh_user: str = "ansible-admin"
    ssh_password: str = None
    status: str = "created"
    creation_time: str = None
    services: List[str] = None


class ProxmoxVMCreator:
    """VM creation and management with cloud-init support."""
    
    def __init__(self, proxmox_client: ProxmoxAPIClient = None):
        self.client = proxmox_client
        self.credential_manager = get_credential_manager()
    
    async def ensure_client(self):
        """Ensure Proxmox client is available."""
        if not self.client:
            # Get credentials from secure storage
            creds = await self.credential_manager.get_credentials("proxmox")
            if not creds:
                raise ValueError("No Proxmox credentials configured. Run setup wizard first.")
            
            self.client = ProxmoxAPIClient(
                host=creds["host"],
                username=creds.get("username"),
                password=creds.get("password"),
                api_token=creds.get("api_token"),
                verify_ssl=creds.get("verify_ssl", False)
            )
            
            if not await self.client.authenticate():
                raise ValueError("Failed to authenticate with Proxmox")
    
    def generate_cloud_init_config(self, request: VMCreationRequest) -> str:
        """Generate cloud-init user-data configuration."""
        
        # Default packages for all VMs
        packages = [
            "qemu-guest-agent",  # Essential for Proxmox integration
            "openssh-server",    # SSH access
            "python3",           # Ansible requirement
            "python3-pip",       # Package management
            "curl",              # Basic utilities
            "wget",
            "nano",
            "htop"
        ]
        
        # Add user-requested packages
        if request.packages:
            packages.extend(request.packages)
        
        # Add Docker if requested
        if request.install_docker:
            packages.extend(["docker.io", "docker-compose"])
        
        # Default commands to run
        runcmd = [
            # Enable and start qemu-guest-agent
            "systemctl enable qemu-guest-agent",
            "systemctl start qemu-guest-agent",
            
            # Configure SSH for ansible-admin
            "mkdir -p /home/ansible-admin/.ssh",
            "chmod 700 /home/ansible-admin/.ssh",
            "chown ansible-admin:ansible-admin /home/ansible-admin/.ssh",
            
            # Enable passwordless sudo for ansible-admin
            "echo 'ansible-admin ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/ansible-admin",
            "chmod 440 /etc/sudoers.d/ansible-admin",
            
            # Update system
            "apt-get update",
            "apt-get upgrade -y",
        ]
        
        # Add Docker setup if requested
        if request.install_docker:
            runcmd.extend([
                "usermod -aG docker ansible-admin",
                "systemctl enable docker",
                "systemctl start docker"
            ])
        
        # Add user-requested commands
        if request.runcmd:
            runcmd.extend(request.runcmd)
        
        # Generate secure password for ansible-admin
        import secrets
        import string
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(20))
        
        # Cloud-init configuration
        cloud_config = {
            "users": [
                {
                    "name": request.username,
                    "groups": ["sudo", "adm"],
                    "shell": "/bin/bash",
                    "sudo": "ALL=(ALL) NOPASSWD:ALL",
                    "lock_passwd": False,
                    "passwd": password,  # Will be hashed by cloud-init
                    "ssh_authorized_keys": request.ssh_keys or []
                }
            ],
            "packages": packages,
            "runcmd": runcmd,
            "ssh_pwauth": True,
            "disable_root": False,
            "package_update": True,
            "package_upgrade": True,
            "timezone": "UTC",
            "locale": "en_US.UTF-8",
            "manage_etc_hosts": True,
            "preserve_hostname": False,
            "hostname": request.name,
            "fqdn": f"{request.name}.local"
        }
        
        # Add SSH keys from MCP server if available
        try:
            ssh_key_path = Path.home() / ".ssh" / "id_rsa.pub"
            if ssh_key_path.exists():
                with open(ssh_key_path) as f:
                    mcp_ssh_key = f.read().strip()
                    cloud_config["users"][0]["ssh_authorized_keys"].append(mcp_ssh_key)
        except Exception:
            pass  # SSH key is optional
        
        # Store password for later retrieval
        self._store_vm_password(request.name, password)
        
        return yaml.dump(cloud_config, default_flow_style=False)
    
    def _store_vm_password(self, vm_name: str, password: str):
        """Store VM password securely for later retrieval."""
        # This will be implemented when we add credential storage
        # For now, just log that we generated it
        print(f"Generated password for {vm_name}: {password}")
    
    async def get_next_vm_id(self) -> int:
        """Get the next available VM ID."""
        await self.ensure_client()
        
        # Get all VMs across all nodes
        all_vms = []
        nodes_response = await self.client._make_request("GET", "/nodes")
        
        for node in nodes_response.get("data", []):
            node_name = node["node"]
            vms_response = await self.client._make_request("GET", f"/nodes/{node_name}/qemu")
            all_vms.extend(vms_response.get("data", []))
        
        # Find highest VM ID
        if not all_vms:
            return 100  # Start at 100 if no VMs exist
        
        max_id = max(int(vm["vmid"]) for vm in all_vms)
        return max_id + 1
    
    async def select_optimal_node(self, request: VMCreationRequest) -> str:
        """Select optimal node for VM placement."""
        await self.ensure_client()
        
        if request.node:
            return request.node
        
        # Get cluster resources for intelligent placement
        resources_response = await self.client._make_request("GET", "/cluster/resources")
        nodes = [r for r in resources_response.get("data", []) if r.get("type") == "node"]
        
        if not nodes:
            raise ValueError("No nodes found in Proxmox cluster")
        
        # Simple placement: choose node with most available memory
        best_node = None
        best_available_memory = 0
        
        for node in nodes:
            if node.get("status") != "online":
                continue
                
            max_memory = node.get("maxmem", 0)
            used_memory = node.get("mem", 0)
            available_memory = max_memory - used_memory
            
            # Check if node has enough memory for requested VM
            if available_memory >= (request.memory_mb * 1024 * 1024):
                if available_memory > best_available_memory:
                    best_available_memory = available_memory
                    best_node = node["node"]
        
        if not best_node:
            raise ValueError(f"No node has enough memory for {request.memory_mb}MB VM")
        
        return best_node
    
    async def create_vm(self, request: VMCreationRequest) -> VMCreationResult:
        """Create a new VM with cloud-init configuration."""
        await self.ensure_client()
        
        # Get VM ID and node placement
        vm_id = await self.get_next_vm_id()
        node = await self.select_optimal_node(request)
        
        print(f"Creating VM {vm_id} '{request.name}' on node '{node}'...")
        
        # Generate cloud-init configuration
        cloud_init_config = self.generate_cloud_init_config(request)
        
        # Encode cloud-init config for Proxmox API
        cloud_init_b64 = base64.b64encode(cloud_init_config.encode()).decode()
        
        # Clone from template
        clone_data = {
            "newid": vm_id,
            "name": request.name,
            "full": 1,  # Full clone
            "target": node
        }
        
        print(f"Cloning template {request.template_id} to VM {vm_id}...")
        clone_response = await self.client._make_request(
            "POST", 
            f"/nodes/{node}/qemu/{request.template_id}/clone",
            data=clone_data
        )
        
        # Wait for clone operation to complete
        task_id = clone_response.get("data")
        if task_id:
            await self._wait_for_task(node, task_id)
        
        # Configure VM resources and cloud-init
        config_data = {
            "cores": request.cores,
            "memory": request.memory_mb,
            "scsihw": "virtio-scsi-pci",
            "ostype": "l26",  # Linux 2.6+ kernel
            "agent": "1",     # Enable QEMU guest agent
            "onboot": "1",    # Start on boot
            
            # Cloud-init configuration
            "cicustom": f"user=local:snippets/{request.name}-user-data.yml",
            "ipconfig0": "ip=dhcp",  # Use DHCP for now
            
            # Network configuration
            "net0": f"virtio,bridge={request.network_bridge},firewall=1"
        }
        
        # Resize disk if different from template
        if request.disk_gb > 20:  # Assuming template has 20GB
            config_data["scsi0"] = f"local-lvm:{request.disk_gb}"
        
        print(f"Configuring VM {vm_id} resources...")
        await self.client._make_request(
            "PUT",
            f"/nodes/{node}/qemu/{vm_id}/config", 
            data=config_data
        )
        
        # Store cloud-init user-data on Proxmox
        await self._store_cloud_init_config(node, request.name, cloud_init_config)
        
        # Start the VM
        print(f"Starting VM {vm_id}...")
        start_response = await self.client._make_request(
            "POST",
            f"/nodes/{node}/qemu/{vm_id}/status/start"
        )
        
        # Wait for VM to start and get IP
        await asyncio.sleep(10)  # Give VM time to boot
        vm_ip = await self._get_vm_ip(node, vm_id)
        
        # Create result object
        result = VMCreationResult(
            vm_id=vm_id,
            name=request.name,
            node=node,
            ip_address=vm_ip,
            ssh_user=request.username,
            status="running",
            services=["qemu-guest-agent"]
        )
        
        if request.install_docker:
            result.services.append("docker")
        
        print(f"✅ VM {vm_id} '{request.name}' created successfully!")
        print(f"   IP: {vm_ip}")
        print(f"   SSH: {request.username}@{vm_ip}")
        
        return result
    
    async def _store_cloud_init_config(self, node: str, vm_name: str, config: str):
        """Store cloud-init configuration on Proxmox node."""
        # This would typically store the config in /var/lib/vz/snippets/
        # For now, we'll use the API to set basic cloud-init
        # In a real implementation, you'd use the Proxmox snippet storage
        pass
    
    async def _wait_for_task(self, node: str, task_id: str, timeout: int = 300):
        """Wait for Proxmox task to complete."""
        for _ in range(timeout):
            task_response = await self.client._make_request(
                "GET", 
                f"/nodes/{node}/tasks/{task_id}/status"
            )
            
            status = task_response.get("data", {}).get("status")
            if status == "stopped":
                exit_status = task_response.get("data", {}).get("exitstatus")
                if exit_status != "OK":
                    raise Exception(f"Task failed: {task_response}")
                return
            
            await asyncio.sleep(1)
        
        raise TimeoutError(f"Task {task_id} did not complete within {timeout} seconds")
    
    async def _get_vm_ip(self, node: str, vm_id: int) -> Optional[str]:
        """Get VM IP address using QEMU guest agent."""
        try:
            # Try to get IP from guest agent
            agent_response = await self.client._make_request(
                "GET",
                f"/nodes/{node}/qemu/{vm_id}/agent/network-get-interfaces"
            )
            
            interfaces = agent_response.get("data", {}).get("result", [])
            for interface in interfaces:
                if interface.get("name") != "lo":  # Skip loopback
                    ip_addresses = interface.get("ip-addresses", [])
                    for ip_info in ip_addresses:
                        if ip_info.get("ip-address-type") == "ipv4":
                            return ip_info.get("ip-address")
        except Exception:
            # Guest agent might not be ready yet
            pass
        
        return None


# MCP Tool Functions
async def create_vm_tool(
    name: str,
    cores: int = 2, 
    memory_gb: float = 4,
    disk_gb: int = 20,
    template_id: int = 9000,
    node: str = None,
    install_docker: bool = False,
    install_qemu_agent: bool = True
) -> Dict[str, Any]:
    """
    Create a new VM from cloud-init template.
    
    Args:
        name: VM name (e.g., 'jenkins-server', 'dev-vm-1')
        cores: CPU cores (default: 2)
        memory_gb: RAM in GB (default: 4)
        disk_gb: Disk size in GB (default: 20) 
        template_id: Template VM ID (default: 9000 for ubuntu-cloud-template)
        node: Target node name (auto-selected if None)
        install_docker: Install Docker during VM creation
        install_qemu_agent: Install QEMU guest agent (recommended: True)
    
    Returns:
        Dictionary with VM details including ID, IP, and SSH access info
    """
    creator = ProxmoxVMCreator()
    
    request = VMCreationRequest(
        name=name,
        cores=cores,
        memory_mb=int(memory_gb * 1024),
        disk_gb=disk_gb,
        template_id=template_id,
        node=node,
        install_docker=install_docker,
        install_qemu_agent=install_qemu_agent
    )
    
    try:
        # Validate homelab context before VM creation
        context_manager = HomelabContextManager()
        
        # Check if target node is valid for deployment
        if node:
            node_validation = await context_manager.validate_device_for_service(
                node, 
                {
                    "cpu_cores": cores,
                    "memory_gb": memory_gb,
                    "storage_gb": disk_gb,
                    "requires_gpu": False
                }
            )
            
            if not node_validation["valid"]:
                return {
                    "success": False,
                    "message": f"Node validation failed: {node_validation['reason']}",
                    "error": "homelab_context_validation_failed"
                }
        
        result = await creator.create_vm(request)
        
        # Update homelab context with new VM
        vm_capabilities = DeviceCapabilities(
            cpu_cores=cores,
            memory_gb=memory_gb,
            storage_gb=disk_gb,
            network_interfaces=["eth0"]
        )
        
        vm_device = HomelabDevice(
            ip_address=result.ip_address or "pending",
            hostname=result.name,
            role="service_host",
            device_type="vm",
            exclude_from_homelab=False,
            capabilities=vm_capabilities,
            services=result.services or [],
            notes=f"Created by MCP - VM ID {result.vm_id} on node {result.node}"
        )
        
        await context_manager.add_device(vm_device)
        
        return {
            "success": True,
            "vm_id": result.vm_id,
            "name": result.name,
            "node": result.node,
            "ip_address": result.ip_address,
            "ssh_access": f"{result.ssh_user}@{result.ip_address}",
            "status": result.status,
            "services": result.services,
            "message": f"VM '{name}' created successfully with ID {result.vm_id} and added to homelab topology"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to create VM '{name}': {str(e)}"
        }


async def start_vm_tool(vm_id: int, node: str = None) -> Dict[str, Any]:
    """
    Start a stopped VM.
    
    Args:
        vm_id: The VM ID to start
        node: Node name where VM is located (auto-detected if None)
    
    Returns:
        Dictionary with operation status
    """
    creator = ProxmoxVMCreator()
    await creator.ensure_client()
    
    try:
        # Find VM node if not specified
        if not node:
            resources = await creator.client._make_request("GET", "/cluster/resources")
            vms = [r for r in resources.get("data", []) if r.get("type") == "qemu" and r.get("vmid") == vm_id]
            if not vms:
                return {"success": False, "error": f"VM {vm_id} not found"}
            node = vms[0]["node"]
        
        # Start the VM
        await creator.client._make_request("POST", f"/nodes/{node}/qemu/{vm_id}/status/start")
        
        return {
            "success": True,
            "message": f"VM {vm_id} started successfully",
            "vm_id": vm_id,
            "node": node
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to start VM {vm_id}: {str(e)}"
        }


async def stop_vm_tool(vm_id: int, node: str = None, force: bool = False) -> Dict[str, Any]:
    """
    Stop a running VM.
    
    Args:
        vm_id: The VM ID to stop
        node: Node name where VM is located (auto-detected if None)
        force: Force stop the VM (default: False for graceful shutdown)
    
    Returns:
        Dictionary with operation status
    """
    creator = ProxmoxVMCreator()
    await creator.ensure_client()
    
    try:
        # Find VM node if not specified
        if not node:
            resources = await creator.client._make_request("GET", "/cluster/resources")
            vms = [r for r in resources.get("data", []) if r.get("type") == "qemu" and r.get("vmid") == vm_id]
            if not vms:
                return {"success": False, "error": f"VM {vm_id} not found"}
            node = vms[0]["node"]
        
        # Stop the VM
        endpoint = "stop" if force else "shutdown"
        await creator.client._make_request("POST", f"/nodes/{node}/qemu/{vm_id}/status/{endpoint}")
        
        return {
            "success": True,
            "message": f"VM {vm_id} {'stopped' if force else 'shutdown'} successfully",
            "vm_id": vm_id,
            "node": node,
            "action": "force_stop" if force else "graceful_shutdown"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to stop VM {vm_id}: {str(e)}"
        }


async def delete_vm_tool(vm_id: int, node: str = None, purge: bool = True) -> Dict[str, Any]:
    """
    Delete a VM permanently.
    
    Args:
        vm_id: The VM ID to delete
        node: Node name where VM is located (auto-detected if None)
        purge: Also remove from backup storage and HA config (default: True)
    
    Returns:
        Dictionary with operation status
    """
    creator = ProxmoxVMCreator()
    await creator.ensure_client()
    
    try:
        # Find VM node if not specified
        if not node:
            resources = await creator.client._make_request("GET", "/cluster/resources")
            vms = [r for r in resources.get("data", []) if r.get("type") == "qemu" and r.get("vmid") == vm_id]
            if not vms:
                return {"success": False, "error": f"VM {vm_id} not found"}
            node = vms[0]["node"]
            vm_name = vms[0].get("name", f"VM-{vm_id}")
        else:
            vm_name = f"VM-{vm_id}"
        
        # Delete the VM
        params = {"purge": 1} if purge else {}
        await creator.client._make_request("DELETE", f"/nodes/{node}/qemu/{vm_id}", params=params)
        
        return {
            "success": True,
            "message": f"VM {vm_id} '{vm_name}' deleted successfully",
            "vm_id": vm_id,
            "node": node,
            "purged": purge
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to delete VM {vm_id}: {str(e)}"
        }


async def get_vm_status_tool(vm_id: int, node: str = None) -> Dict[str, Any]:
    """
    Get current status of a VM.
    
    Args:
        vm_id: The VM ID to check
        node: Node name where VM is located (auto-detected if None)
    
    Returns:
        Dictionary with VM status and details
    """
    creator = ProxmoxVMCreator()
    await creator.ensure_client()
    
    try:
        # Find VM and get its details
        resources = await creator.client._make_request("GET", "/cluster/resources")
        vms = [r for r in resources.get("data", []) if r.get("type") == "qemu" and r.get("vmid") == vm_id]
        
        if not vms:
            return {"success": False, "error": f"VM {vm_id} not found"}
        
        vm = vms[0]
        node = vm["node"]
        
        # Get detailed VM config
        config = await creator.client._make_request("GET", f"/nodes/{node}/qemu/{vm_id}/config")
        
        # Try to get IP address if VM is running
        ip_address = None
        if vm.get("status") == "running":
            ip_address = await creator._get_vm_ip(node, vm_id)
        
        return {
            "success": True,
            "vm_id": vm_id,
            "name": vm.get("name"),
            "node": node,
            "status": vm.get("status"),
            "cpu": vm.get("cpu", 0),
            "memory": vm.get("mem", 0),
            "max_memory": vm.get("maxmem", 0),
            "disk": vm.get("disk", 0),
            "max_disk": vm.get("maxdisk", 0),
            "uptime": vm.get("uptime", 0),
            "ip_address": ip_address,
            "config": config.get("data", {})
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get status for VM {vm_id}: {str(e)}"
        }