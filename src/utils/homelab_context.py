"""
Homelab Context Manager - Manages homelab topology and device roles
"""

import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from ipaddress import IPv4Network, IPv4Address
import subprocess
import socket

from .credential_manager import CredentialManager


@dataclass
class DeviceCapabilities:
    """Device hardware capabilities"""
    cpu_cores: int
    memory_gb: int
    storage_gb: int
    network_interfaces: List[str]
    gpu: Optional[Dict[str, Any]] = None


@dataclass
class AuthenticationInfo:
    """Authentication information for a device"""
    ansible_user: str = "ansible-admin"
    github_username: Optional[str] = None
    ssh_keys_deployed: List[str] = None
    auth_method: str = "ssh_key"  # ssh_key, password, key_file
    sudo_access: bool = True
    last_verified: Optional[str] = None
    setup_completed: bool = False
    
    def __post_init__(self):
        if self.ssh_keys_deployed is None:
            self.ssh_keys_deployed = []


@dataclass
class HomelabDevice:
    """Represents a device in the homelab"""
    ip_address: str
    hostname: str
    role: str
    device_type: str
    exclude_from_homelab: bool
    capabilities: DeviceCapabilities
    services: List[str]
    notes: str
    discovered_at: Optional[str] = None
    last_verified: Optional[str] = None
    managed_vms: Optional[List[str]] = None
    authentication: Optional[AuthenticationInfo] = None


@dataclass
class HomelabService:
    """Represents a service running in the homelab"""
    name: str
    category: str
    port: int
    protocol: str
    hosted_on: str
    status: str
    dependencies: List[str]
    managed_by: str


@dataclass
class NetworkSegment:
    """Represents a network segment in the homelab"""
    name: str
    role: str
    gateway: str
    dns_servers: List[str]
    vlan_id: Optional[int] = None
    managed_by: str = "router"


class HomelabContextManager:
    """Manages homelab topology context and device discovery"""
    
    def __init__(self, inventory_dir: str = "inventory"):
        self.inventory_dir = Path(inventory_dir)
        self.topology_file = self.inventory_dir / "homelab-topology.json"
        self.credential_manager = CredentialManager()
        
        # Ensure inventory directory exists
        self.inventory_dir.mkdir(exist_ok=True)
        
        # Initialize empty topology if file doesn't exist
        if not self.topology_file.exists():
            self._create_default_topology()
    
    def _create_default_topology(self):
        """Create default topology structure"""
        default_topology = {
            "topology": {
                "version": "1.0",
                "last_updated": None,
                "discovery_settings": {
                    "auto_discovery_enabled": True,
                    "staleness_hours": 10,
                    "network_scan_range": "192.168.10.0/24"
                }
            },
            "devices": {},
            "networks": {},
            "services": {},
            "device_roles": {
                "development": {
                    "description": "Development machines - excluded from homelab deployment",
                    "allow_service_deployment": False,
                    "monitoring_level": "basic"
                },
                "infrastructure_host": {
                    "description": "Core infrastructure servers (Proxmox, Docker hosts)",
                    "allow_service_deployment": False,
                    "monitoring_level": "detailed"
                },
                "service_host": {
                    "description": "Dedicated service hosts (Pi devices, VMs)",
                    "allow_service_deployment": True,
                    "monitoring_level": "detailed"
                },
                "network_device": {
                    "description": "Routers, switches, access points",
                    "allow_service_deployment": False,
                    "monitoring_level": "basic"
                },
                "storage_device": {
                    "description": "NAS, SAN, backup devices",
                    "allow_service_deployment": False,
                    "monitoring_level": "detailed"
                }
            },
            "deployment_preferences": {
                "default_vm_host": None,
                "preferred_service_hosts": [],
                "resource_allocation": {
                    "cpu_overcommit_ratio": 2.0,
                    "memory_overcommit_ratio": 1.5,
                    "storage_threshold_percent": 85
                }
            }
        }
        
        with open(self.topology_file, 'w') as f:
            json.dump(default_topology, f, indent=2)
    
    async def load_topology(self) -> Dict[str, Any]:
        """Load homelab topology from storage"""
        try:
            with open(self.topology_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self._create_default_topology()
            return await self.load_topology()
    
    async def save_topology(self, topology: Dict[str, Any]):
        """Save homelab topology to storage"""
        topology["topology"]["last_updated"] = datetime.now().isoformat()
        
        with open(self.topology_file, 'w') as f:
            json.dump(topology, f, indent=2)
    
    async def is_context_stale(self) -> bool:
        """Check if homelab context is stale"""
        topology = await self.load_topology()
        last_updated = topology["topology"].get("last_updated")
        
        if not last_updated:
            return True
        
        staleness_hours = topology["topology"]["discovery_settings"]["staleness_hours"]
        last_update_time = datetime.fromisoformat(last_updated)
        staleness_threshold = datetime.now() - timedelta(hours=staleness_hours)
        
        return last_update_time < staleness_threshold
    
    async def add_device(self, device: HomelabDevice) -> bool:
        """Add a device to the homelab topology"""
        topology = await self.load_topology()
        
        device_dict = asdict(device)
        device_dict["discovered_at"] = datetime.now().isoformat()
        device_dict["last_verified"] = datetime.now().isoformat()
        
        topology["devices"][device.ip_address] = device_dict
        await self.save_topology(topology)
        
        return True
    
    async def get_device(self, ip_address: str) -> Optional[HomelabDevice]:
        """Get device by IP address"""
        topology = await self.load_topology()
        device_data = topology["devices"].get(ip_address)
        
        if not device_data:
            return None
        
        # Convert capabilities dict back to DeviceCapabilities object
        capabilities_data = device_data["capabilities"]
        capabilities = DeviceCapabilities(**capabilities_data)
        device_data["capabilities"] = capabilities
        
        # Convert authentication dict back to AuthenticationInfo object if present
        if "authentication" in device_data and device_data["authentication"]:
            auth_data = device_data["authentication"]
            device_data["authentication"] = AuthenticationInfo(**auth_data)
        
        return HomelabDevice(**device_data)
    
    async def get_deployable_devices(self) -> List[HomelabDevice]:
        """Get devices that can have services deployed to them"""
        topology = await self.load_topology()
        deployable_devices = []
        
        for ip_address, device_data in topology["devices"].items():
            if not device_data.get("exclude_from_homelab", False):
                role = device_data.get("role")
                role_config = topology["device_roles"].get(role, {})
                
                if role_config.get("allow_service_deployment", False):
                    capabilities = DeviceCapabilities(**device_data["capabilities"])
                    device_data["capabilities"] = capabilities
                    deployable_devices.append(HomelabDevice(**device_data))
        
        return deployable_devices
    
    async def discover_network_devices(self, network_range: str = None) -> List[str]:
        """Discover devices on the network using nmap"""
        topology = await self.load_topology()
        
        if not network_range:
            network_range = topology["topology"]["discovery_settings"]["network_scan_range"]
        
        try:
            # Use nmap to discover live hosts
            result = subprocess.run([
                "nmap", "-sn", network_range
            ], capture_output=True, text=True, timeout=60)
            
            # Parse nmap output for IP addresses
            discovered_ips = []
            for line in result.stdout.split('\n'):
                if "Nmap scan report for" in line:
                    # Extract IP address from line like "Nmap scan report for 192.168.10.100"
                    parts = line.split()
                    if len(parts) >= 5:
                        ip = parts[-1].strip('()')
                        discovered_ips.append(ip)
            
            return discovered_ips
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Fallback to simple ping sweep if nmap not available
            return await self._ping_sweep(network_range)
    
    async def _ping_sweep(self, network_range: str) -> List[str]:
        """Fallback ping sweep discovery"""
        network = IPv4Network(network_range)
        discovered_ips = []
        
        # Limit to reasonable subnet size
        if network.num_addresses > 254:
            network = IPv4Network(f"{network.network_address}/24")
        
        tasks = []
        for ip in network.hosts():
            tasks.append(self._ping_host(str(ip)))
        
        # Run pings concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for ip, is_alive in zip(network.hosts(), results):
            if is_alive and not isinstance(is_alive, Exception):
                discovered_ips.append(str(ip))
        
        return discovered_ips
    
    async def _ping_host(self, ip: str) -> bool:
        """Ping a single host"""
        try:
            result = subprocess.run([
                "ping", "-c", "1", "-W", "1000", ip
            ], capture_output=True, timeout=2)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    async def get_device_hostname(self, ip: str) -> str:
        """Get hostname for an IP address"""
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except (socket.herror, socket.gaierror):
            return f"unknown-{ip.replace('.', '-')}"
    
    async def update_device_authentication(
        self,
        ip_address: str,
        github_username: Optional[str] = None,
        ssh_keys: Optional[List[str]] = None,
        ansible_user: str = "ansible-admin",
        auth_method: str = "ssh_key",
        sudo_access: bool = True
    ) -> bool:
        """Update authentication information for a device"""
        try:
            topology = await self.load_topology()
            
            # Get or create device entry
            if ip_address not in topology["devices"]:
                # Create a basic device entry if it doesn't exist
                hostname = await self.get_device_hostname(ip_address)
                topology["devices"][ip_address] = {
                    "ip_address": ip_address,
                    "hostname": hostname,
                    "role": "server",
                    "device_type": "unknown",
                    "exclude_from_homelab": False,
                    "capabilities": {
                        "cpu_cores": 0,
                        "memory_gb": 0,
                        "storage_gb": 0,
                        "network_interfaces": []
                    },
                    "services": [],
                    "notes": "Auto-created during authentication setup",
                    "discovered_at": datetime.now().isoformat()
                }
            
            # Update authentication info
            auth_info = {
                "ansible_user": ansible_user,
                "github_username": github_username,
                "ssh_keys_deployed": ssh_keys or [],
                "auth_method": auth_method,
                "sudo_access": sudo_access,
                "last_verified": datetime.now().isoformat(),
                "setup_completed": True
            }
            
            topology["devices"][ip_address]["authentication"] = auth_info
            topology["topology"]["last_updated"] = datetime.now().isoformat()
            
            # Save updated topology
            await self.save_topology(topology)
            return True
            
        except Exception as e:
            print(f"Failed to update authentication for {ip_address}: {e}")
            return False
    
    async def get_device_authentication(self, ip_address: str) -> Optional[AuthenticationInfo]:
        """Get authentication information for a device"""
        device = await self.get_device(ip_address)
        return device.authentication if device else None
    
    async def get_github_username_from_context(self) -> Optional[str]:
        """Get the GitHub username from any authenticated device in context"""
        topology = await self.load_topology()
        
        for device_data in topology["devices"].values():
            auth_info = device_data.get("authentication")
            if auth_info and auth_info.get("github_username"):
                return auth_info["github_username"]
        
        return None
    
    async def list_authenticated_devices(self) -> List[Dict[str, Any]]:
        """List all devices with authentication information"""
        topology = await self.load_topology()
        authenticated_devices = []
        
        for ip_address, device_data in topology["devices"].items():
            auth_info = device_data.get("authentication")
            if auth_info and auth_info.get("setup_completed"):
                authenticated_devices.append({
                    "ip_address": ip_address,
                    "hostname": device_data.get("hostname"),
                    "ansible_user": auth_info.get("ansible_user"),
                    "github_username": auth_info.get("github_username"),
                    "auth_method": auth_info.get("auth_method"),
                    "last_verified": auth_info.get("last_verified"),
                    "sudo_access": auth_info.get("sudo_access")
                })
        
        return authenticated_devices
    
    async def classify_device_role(self, ip: str, capabilities: DeviceCapabilities) -> str:
        """Classify device role based on capabilities and heuristics"""
        # Check if it's a known infrastructure device
        if ip in await self._get_known_infrastructure_ips():
            return "infrastructure_host"
        
        # Check if it's a high-capability device (likely server)
        if capabilities.cpu_cores >= 8 and capabilities.memory_gb >= 16:
            return "infrastructure_host"
        
        # Check if it's a low-power device (likely Pi or similar)
        if capabilities.cpu_cores <= 4 and capabilities.memory_gb <= 8:
            return "service_host"
        
        # Default to service host for unknown devices
        return "service_host"
    
    async def _get_known_infrastructure_ips(self) -> Set[str]:
        """Get known infrastructure IP addresses"""
        # Check Proxmox credentials for known hosts
        proxmox_creds = await self.credential_manager.get_credentials("proxmox")
        known_ips = set()
        
        if proxmox_creds:
            host = proxmox_creds.get("host", "").replace("https://", "").replace("http://", "")
            if ":" in host:
                host = host.split(":")[0]
            known_ips.add(host)
        
        return known_ips
    
    async def validate_device_for_service(self, ip: str, service_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Validate if a device can host a specific service"""
        device = await self.get_device(ip)
        
        if not device:
            return {
                "valid": False,
                "reason": "Device not found in homelab topology"
            }
        
        if device.exclude_from_homelab:
            return {
                "valid": False,
                "reason": "Device excluded from homelab deployments"
            }
        
        topology = await self.load_topology()
        role_config = topology["device_roles"].get(device.role, {})
        
        if not role_config.get("allow_service_deployment", False):
            return {
                "valid": False,
                "reason": f"Device role '{device.role}' does not allow service deployment"
            }
        
        # Check resource requirements
        required_cpu = service_requirements.get("cpu_cores", 0)
        required_memory = service_requirements.get("memory_gb", 0)
        required_storage = service_requirements.get("storage_gb", 0)
        
        if device.capabilities.cpu_cores < required_cpu:
            return {
                "valid": False,
                "reason": f"Insufficient CPU cores: has {device.capabilities.cpu_cores}, needs {required_cpu}"
            }
        
        if device.capabilities.memory_gb < required_memory:
            return {
                "valid": False,
                "reason": f"Insufficient memory: has {device.capabilities.memory_gb}GB, needs {required_memory}GB"
            }
        
        if device.capabilities.storage_gb < required_storage:
            return {
                "valid": False,
                "reason": f"Insufficient storage: has {device.capabilities.storage_gb}GB, needs {required_storage}GB"
            }
        
        return {
            "valid": True,
            "reason": "Device meets all requirements"
        }
    
    async def refresh_topology(self) -> Dict[str, Any]:
        """Refresh the entire homelab topology"""
        topology = await self.load_topology()
        
        # Discover network devices
        network_range = topology["topology"]["discovery_settings"]["network_scan_range"]
        discovered_ips = await self.discover_network_devices(network_range)
        
        # Track discovery stats
        stats = {
            "discovered_devices": len(discovered_ips),
            "new_devices": 0,
            "updated_devices": 0,
            "errors": []
        }
        
        for ip in discovered_ips:
            try:
                existing_device = await self.get_device(ip)
                
                if not existing_device:
                    # New device discovered
                    hostname = await self.get_device_hostname(ip)
                    
                    # Basic device discovery - in a real implementation,
                    # this would probe the device for actual capabilities
                    capabilities = DeviceCapabilities(
                        cpu_cores=0,  # Unknown
                        memory_gb=0,  # Unknown
                        storage_gb=0,  # Unknown
                        network_interfaces=[]
                    )
                    
                    role = await self.classify_device_role(ip, capabilities)
                    
                    new_device = HomelabDevice(
                        ip_address=ip,
                        hostname=hostname,
                        role=role,
                        device_type="unknown",
                        exclude_from_homelab=False,
                        capabilities=capabilities,
                        services=[],
                        notes="Auto-discovered device - needs manual configuration"
                    )
                    
                    await self.add_device(new_device)
                    stats["new_devices"] += 1
                    
                else:
                    # Update existing device
                    existing_device.last_verified = datetime.now().isoformat()
                    await self.add_device(existing_device)
                    stats["updated_devices"] += 1
                    
            except Exception as e:
                stats["errors"].append(f"Error processing {ip}: {str(e)}")
        
        return stats
    
    async def update_terraform_context(self, vm_name: str, terraform_context: Dict[str, Any]) -> None:
        """Store Terraform state information in homelab context."""
        topology = await self.load_topology()
        
        # Initialize terraform section if it doesn't exist
        if "terraform_state" not in topology:
            topology["terraform_state"] = {}
        
        topology["terraform_state"][vm_name] = terraform_context
        await self.save_topology(topology)
    
    async def get_terraform_context(self, vm_name: str) -> Optional[Dict[str, Any]]:
        """Get Terraform state information for a VM."""
        topology = await self.load_topology()
        return topology.get("terraform_state", {}).get(vm_name)
    
    async def remove_terraform_context(self, vm_name: str) -> None:
        """Remove Terraform state information for a VM."""
        topology = await self.load_topology()
        if "terraform_state" in topology and vm_name in topology["terraform_state"]:
            del topology["terraform_state"][vm_name]
            await self.save_topology(topology)
    
    async def list_terraform_managed_vms(self) -> List[Dict[str, Any]]:
        """List all VMs managed by Terraform."""
        topology = await self.load_topology()
        terraform_state = topology.get("terraform_state", {})
        
        return [
            {
                "vm_name": vm_name,
                "terraform_state_dir": context.get("terraform_state_dir"),
                "created_at": context.get("created_at"),
                "vm_id": context.get("terraform_outputs", {}).get("vm_id", {}).get("value"),
                "node_name": context.get("terraform_outputs", {}).get("node_name", {}).get("value")
            }
            for vm_name, context in terraform_state.items()
        ]
    
    async def update_ansible_execution_context(self, execution_name: str, execution_context: Dict[str, Any]) -> None:
        """Store Ansible execution context in homelab topology."""
        topology = await self.load_topology()
        
        # Initialize ansible_executions section if it doesn't exist
        if "ansible_executions" not in topology:
            topology["ansible_executions"] = {}
        
        topology["ansible_executions"][execution_name] = execution_context
        await self.save_topology(topology)
    
    async def get_ansible_execution_context(self, execution_name: str) -> Optional[Dict[str, Any]]:
        """Get specific Ansible execution context."""
        topology = await self.load_topology()
        return topology.get("ansible_executions", {}).get(execution_name)
    
    async def list_ansible_executions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent Ansible executions."""
        topology = await self.load_topology()
        ansible_executions = topology.get("ansible_executions", {})
        
        # Sort by execution time, most recent first
        executions = list(ansible_executions.values())
        executions.sort(key=lambda x: x.get("executed_at", ""), reverse=True)
        
        return executions[:limit]