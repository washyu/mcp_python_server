"""
Proxmox API client for discovery and management operations.
"""

import asyncio
import aiohttp
import ssl
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProxmoxGPU:
    """Represents a GPU device on a Proxmox node."""
    pci_id: str
    vendor: str
    device: str
    model: str
    memory: Optional[str] = None
    driver: Optional[str] = None
    suitable_for: List[str] = None
    
    def __post_init__(self):
        if self.suitable_for is None:
            self.suitable_for = []

@dataclass
class ProxmoxCPU:
    """Represents CPU details on a Proxmox node."""
    model: str
    cores: int
    threads: int
    frequency: Optional[str] = None
    features: List[str] = None
    
    def __post_init__(self):
        if self.features is None:
            self.features = []

@dataclass
class ProxmoxStorage:
    """Represents storage device details."""
    device: str
    type: str
    model: str
    size: str
    read_speed: Optional[str] = None
    write_speed: Optional[str] = None

@dataclass
class ProxmoxNodeHardware:
    """Enhanced hardware details for a Proxmox node."""
    gpus: List[ProxmoxGPU] = None
    cpu_details: Optional[ProxmoxCPU] = None
    storage_devices: List[ProxmoxStorage] = None
    
    def __post_init__(self):
        if self.gpus is None:
            self.gpus = []
        if self.storage_devices is None:
            self.storage_devices = []

@dataclass
class ProxmoxNode:
    """Represents a Proxmox cluster node."""
    node: str
    status: str
    cpu: float
    maxcpu: int
    mem: int
    maxmem: int
    disk: int
    maxdisk: int
    uptime: int
    level: str = ""
    id: str = ""
    hardware: Optional[ProxmoxNodeHardware] = None


class ProxmoxAPIClient:
    """Client for interacting with Proxmox VE API."""
    
    def __init__(self, host: str, username: str = None, password: str = None, 
                 api_token: str = None, verify_ssl: bool = False):
        """
        Initialize Proxmox API client.
        
        Args:
            host: Proxmox host (IP or hostname)
            username: Username (e.g., root@pam) - for password auth
            password: Password - for password auth
            api_token: API token (e.g., root@pam!tokenid=uuid) - for token auth
            verify_ssl: Whether to verify SSL certificates
        """
        self.host = host.rstrip('/')
        if not self.host.startswith(('http://', 'https://')):
            self.host = f"https://{self.host}"
        
        # Auth method detection
        self.use_token_auth = bool(api_token)
        self.api_token = api_token
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        
        # Auth tokens (for password auth)
        self.ticket: Optional[str] = None
        self.csrf_token: Optional[str] = None
        
        # SSL context
        self.ssl_context = None
        if not verify_ssl:
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
    
    async def authenticate(self) -> bool:
        """
        Authenticate with Proxmox API.
        
        For API tokens, no authentication is needed.
        For password auth, gets ticket from API.
        
        Returns:
            True if authentication successful or using token
        """
        # API tokens don't need authentication
        if self.use_token_auth:
            logger.info("Using API token authentication")
            return True
        
        # Password authentication
        if not self.username or not self.password:
            logger.error("Username and password required for ticket authentication")
            return False
        
        auth_url = f"{self.host}:8006/api2/json/access/ticket"
        
        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        
        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                auth_data = {
                    'username': self.username,
                    'password': self.password
                }
                
                async with session.post(auth_url, data=auth_data) as resp:
                    if resp.status != 200:
                        logger.error(f"Authentication failed: {resp.status}")
                        return False
                    
                    data = await resp.json()
                    self.ticket = data['data']['ticket']
                    self.csrf_token = data['data']['CSRFPreventionToken']
                    
                    logger.info(f"Successfully authenticated as {self.username}")
                    return True
                    
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make authenticated request to Proxmox API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., /nodes)
            data: Optional data for POST requests
            
        Returns:
            JSON response data
        """
        url = f"{self.host}:8006/api2/json{endpoint}"
        headers = {}
        
        if self.use_token_auth:
            # API token authentication
            headers['Authorization'] = f"PVEAPIToken={self.api_token}"
            # No CSRF token needed for API tokens
        else:
            # Ticket authentication
            if not self.ticket:
                raise Exception("Not authenticated. Call authenticate() first.")
            
            headers['Cookie'] = f"PVEAuthCookie={self.ticket}"
            
            # CSRF token needed for non-GET requests with ticket auth
            if method != "GET":
                headers['CSRFPreventionToken'] = self.csrf_token
        
        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.request(method, url, headers=headers, data=data) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"API request failed: {resp.status} - {error_text}")
                
                return await resp.json()
    
    async def list_nodes(self) -> List[ProxmoxNode]:
        """
        List all nodes in the Proxmox cluster.
        
        Returns:
            List of ProxmoxNode objects
            
        API Documentation:
        GET /api2/json/nodes
        https://pve.proxmox.com/pve-docs/api-viewer/index.html#/nodes
        """
        try:
            response = await self._make_request("GET", "/nodes")
            nodes = []
            
            for node_data in response.get('data', []):
                node = ProxmoxNode(
                    node=node_data.get('node', ''),
                    status=node_data.get('status', 'unknown'),
                    cpu=node_data.get('cpu', 0.0),
                    maxcpu=node_data.get('maxcpu', 0),
                    mem=node_data.get('mem', 0),
                    maxmem=node_data.get('maxmem', 0),
                    disk=node_data.get('disk', 0),
                    maxdisk=node_data.get('maxdisk', 0),
                    uptime=node_data.get('uptime', 0),
                    level=node_data.get('level', ''),
                    id=node_data.get('id', '')
                )
                nodes.append(node)
            
            return nodes
            
        except Exception as e:
            logger.error(f"Failed to list nodes: {e}")
            raise
    
    async def list_vms(self) -> List[Dict[str, Any]]:
        """List all virtual machines across all nodes."""
        try:
            # Get list of nodes first
            nodes_response = await self._make_request("GET", "/nodes")
            nodes = [node["node"] for node in nodes_response.get("data", [])]
            
            all_vms = []
            for node in nodes:
                try:
                    # Get VMs for this node
                    vms_response = await self._make_request("GET", f"/nodes/{node}/qemu")
                    for vm in vms_response.get("data", []):
                        vm["node"] = node  # Add node info
                        all_vms.append(vm)
                except Exception as e:
                    logger.warning(f"Failed to get VMs for node {node}: {e}")
                    continue
            
            return all_vms
            
        except Exception as e:
            logger.error(f"Failed to list VMs: {e}")
            return []
    
    async def list_storage(self) -> List[Dict[str, Any]]:
        """List all storage pools."""
        try:
            response = await self._make_request("GET", "/storage")
            storage_pools = response.get("data", [])
            
            # Get detailed storage info for each pool
            detailed_storage = []
            for pool in storage_pools:
                storage_id = pool.get("storage", "")
                try:
                    # Get usage info for this storage
                    detail_response = await self._make_request("GET", f"/storage/{storage_id}")
                    pool_detail = detail_response.get("data", {})
                    
                    # Merge basic info with detailed info
                    combined = {**pool, **pool_detail}
                    detailed_storage.append(combined)
                except Exception as e:
                    logger.warning(f"Failed to get details for storage {storage_id}: {e}")
                    detailed_storage.append(pool)  # Use basic info
            
            return detailed_storage
            
        except Exception as e:
            logger.error(f"Failed to list storage: {e}")
            return []
    
    async def list_networks(self) -> List[Dict[str, Any]]:
        """List all network interfaces across all nodes."""
        try:
            # Get list of nodes first
            nodes_response = await self._make_request("GET", "/nodes")
            nodes = [node["node"] for node in nodes_response.get("data", [])]
            
            all_networks = []
            for node in nodes:
                try:
                    # Get network interfaces for this node
                    net_response = await self._make_request("GET", f"/nodes/{node}/network")
                    for network in net_response.get("data", []):
                        network["node"] = node  # Add node info
                        all_networks.append(network)
                except Exception as e:
                    logger.warning(f"Failed to get networks for node {node}: {e}")
                    continue
            
            return all_networks
            
        except Exception as e:
            logger.error(f"Failed to list networks: {e}")
            return []
    
    async def list_templates(self) -> List[Dict[str, Any]]:
        """List all VM templates across all nodes."""
        try:
            # Get list of nodes first
            nodes_response = await self._make_request("GET", "/nodes")
            nodes = [node["node"] for node in nodes_response.get("data", [])]
            
            all_templates = []
            for node in nodes:
                try:
                    # Get VMs for this node
                    vms_response = await self._make_request("GET", f"/nodes/{node}/qemu")
                    for vm in vms_response.get("data", []):
                        # Check if this VM is a template
                        if vm.get("template", 0) == 1:
                            vm["node"] = node  # Add node info
                            all_templates.append(vm)
                except Exception as e:
                    logger.warning(f"Failed to get templates for node {node}: {e}")
                    continue
            
            return all_templates
            
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return []
    
    async def create_api_token(self, userid: str, tokenid: str, comment: str = "", 
                              expire: int = 0, privsep: bool = True) -> Dict[str, Any]:
        """
        Create an API token for a user.
        
        Args:
            userid: Full User ID (e.g., 'root@pam')
            tokenid: Token ID (e.g., 'mcp-server')
            comment: Optional comment
            expire: Expiration time in seconds (0 = never)
            privsep: Enable privilege separation
            
        Returns:
            Dict with 'full-tokenid' and 'value' (the actual token)
            
        API Documentation:
        POST /api2/json/access/users/{userid}/token/{tokenid}
        """
        # Must use password auth to create tokens
        if self.use_token_auth:
            raise Exception("Cannot create tokens using token authentication. Use password auth.")
        
        endpoint = f"/access/users/{userid}/token/{tokenid}"
        data = {
            "comment": comment,
            "expire": expire,
            "privsep": 1 if privsep else 0
        }
        
        try:
            response = await self._make_request("POST", endpoint, data)
            token_data = response.get('data', {})
            
            # The response includes the full token format
            full_tokenid = token_data.get('full-tokenid', f"{userid}!{tokenid}")
            token_value = token_data.get('value', '')
            
            return {
                'full-tokenid': full_tokenid,
                'value': token_value,
                'info': token_data.get('info', {})
            }
            
        except Exception as e:
            logger.error(f"Failed to create API token: {e}")
            raise
    
    async def delete_api_token(self, userid: str, tokenid: str) -> bool:
        """
        Delete an API token.
        
        Args:
            userid: Full User ID (e.g., 'root@pam')
            tokenid: Token ID to delete
            
        Returns:
            True if successful
        """
        endpoint = f"/access/users/{userid}/token/{tokenid}"
        
        try:
            await self._make_request("DELETE", endpoint)
            return True
        except Exception as e:
            logger.error(f"Failed to delete API token: {e}")
            return False
    
    async def list_api_tokens(self, userid: str) -> List[Dict[str, Any]]:
        """
        List all API tokens for a user.
        
        Args:
            userid: Full User ID (e.g., 'root@pam')
            
        Returns:
            List of token information
        """
        endpoint = f"/access/users/{userid}/token"
        
        try:
            response = await self._make_request("GET", endpoint)
            return response.get('data', [])
        except Exception as e:
            logger.error(f"Failed to list API tokens: {e}")
            return []
    
    async def discover_node_hardware(self, node_name: str) -> ProxmoxNodeHardware:
        """
        Discover detailed hardware capabilities of a Proxmox node.
        
        Args:
            node_name: Name of the node to discover
            
        Returns:
            ProxmoxNodeHardware with discovered components
        """
        hardware = ProxmoxNodeHardware()
        
        try:
            # Discover GPUs
            hardware.gpus = await self._discover_gpus(node_name)
            
            # Discover CPU details
            hardware.cpu_details = await self._discover_cpu_details(node_name)
            
            # Discover storage devices
            hardware.storage_devices = await self._discover_storage_devices(node_name)
            
            logger.info(f"Discovered hardware for node {node_name}: {len(hardware.gpus)} GPUs, "
                       f"CPU: {hardware.cpu_details.model if hardware.cpu_details else 'Unknown'}")
            
        except Exception as e:
            logger.error(f"Failed to discover hardware for node {node_name}: {e}")
        
        return hardware
    
    async def _discover_gpus(self, node_name: str) -> List[ProxmoxGPU]:
        """Discover GPU devices on a node."""
        gpus = []
        
        try:
            # Get PCI devices from Proxmox API
            endpoint = f"/nodes/{node_name}/hardware/pci"
            response = await self._make_request("GET", endpoint)
            
            for device in response.get('data', []):
                # Look for GPU devices (VGA controller, 3D controller, Display controller)
                device_class = device.get('class', '').lower()
                vendor = device.get('vendor', 'Unknown')
                device_name = device.get('device', 'Unknown')
                pci_id = device.get('id', '')
                
                if any(gpu_class in device_class for gpu_class in ['vga', '3d', 'display']):
                    # Determine GPU capabilities
                    suitable_for = self._classify_gpu_capabilities(vendor, device_name)
                    
                    gpu = ProxmoxGPU(
                        pci_id=pci_id,
                        vendor=vendor,
                        device=device_name,
                        model=f"{vendor} {device_name}",
                        suitable_for=suitable_for
                    )
                    gpus.append(gpu)
                    
        except Exception as e:
            logger.warning(f"Could not discover GPUs for node {node_name}: {e}")
            
        return gpus
    
    def _classify_gpu_capabilities(self, vendor: str, device: str) -> List[str]:
        """Classify GPU capabilities based on vendor and model."""
        vendor_lower = vendor.lower()
        device_lower = device.lower()
        capabilities = []
        
        # AMD GPUs
        if 'amd' in vendor_lower or 'ati' in vendor_lower:
            if any(model in device_lower for model in ['mi50', 'mi100', 'mi200', 'instinct']):
                capabilities.extend(['ai_training', 'compute', 'opencl', 'rocm'])
            elif any(model in device_lower for model in ['rx', 'radeon']):
                capabilities.extend(['gaming', 'compute', 'opencl'])
            else:
                capabilities.extend(['display', 'compute'])
        
        # NVIDIA GPUs
        elif 'nvidia' in vendor_lower:
            if any(model in device_lower for model in ['tesla', 'quadro', 'a100', 'v100']):
                capabilities.extend(['ai_training', 'compute', 'cuda'])
            elif any(model in device_lower for model in ['rtx', 'gtx', 'geforce']):
                capabilities.extend(['gaming', 'ai_training', 'cuda'])
            else:
                capabilities.extend(['display', 'compute'])
        
        # Intel GPUs
        elif 'intel' in vendor_lower:
            if 'arc' in device_lower:
                capabilities.extend(['gaming', 'compute'])
            else:
                capabilities.extend(['display'])
        
        # Default for unknown
        if not capabilities:
            capabilities.append('display')
            
        return capabilities
    
    async def _discover_cpu_details(self, node_name: str) -> Optional[ProxmoxCPU]:
        """Discover detailed CPU information."""
        try:
            # Get CPU info from Proxmox API
            endpoint = f"/nodes/{node_name}/status"
            response = await self._make_request("GET", endpoint)
            
            cpu_info = response.get('data', {}).get('cpuinfo', {})
            
            if cpu_info:
                # Extract CPU details
                model = cpu_info.get('model', 'Unknown CPU')
                cores = cpu_info.get('cores', 0)
                threads = cpu_info.get('cpus', cores)  # Total threads
                frequency = cpu_info.get('mhz', 'Unknown')
                
                # Format frequency
                if isinstance(frequency, (int, float)):
                    frequency = f"{frequency/1000:.1f}GHz"
                
                # Extract CPU features (simplified)
                features = []
                flags = cpu_info.get('flags', '')
                if isinstance(flags, str):
                    common_features = ['sse', 'avx', 'avx2', 'avx512', 'aes', 'vmx', 'svm']
                    features = [f for f in common_features if f in flags.lower()]
                
                return ProxmoxCPU(
                    model=model,
                    cores=cores,
                    threads=threads,
                    frequency=frequency,
                    features=features
                )
                
        except Exception as e:
            logger.warning(f"Could not discover CPU details for node {node_name}: {e}")
            
        return None
    
    async def _discover_storage_devices(self, node_name: str) -> List[ProxmoxStorage]:
        """Discover storage device details."""
        storage_devices = []
        
        try:
            # Get disk info from Proxmox API
            endpoint = f"/nodes/{node_name}/disks/list"
            response = await self._make_request("GET", endpoint)
            
            for disk in response.get('data', []):
                device_name = disk.get('devpath', disk.get('device', 'Unknown'))
                size = disk.get('size', 0)
                model = disk.get('model', 'Unknown')
                
                # Determine storage type
                storage_type = self._classify_storage_type(device_name, model)
                
                # Format size
                size_str = self._format_storage_size(size)
                
                storage = ProxmoxStorage(
                    device=device_name,
                    type=storage_type,
                    model=model,
                    size=size_str
                )
                storage_devices.append(storage)
                
        except Exception as e:
            logger.warning(f"Could not discover storage for node {node_name}: {e}")
            
        return storage_devices
    
    def _classify_storage_type(self, device_path: str, model: str) -> str:
        """Classify storage device type based on device path and model."""
        device_lower = device_path.lower()
        model_lower = model.lower()
        
        if '/dev/nvme' in device_lower:
            return 'NVMe SSD'
        elif any(indicator in model_lower for indicator in ['ssd', 'solid']):
            return 'SATA SSD'
        elif any(indicator in model_lower for indicator in ['hdd', 'disk', 'drive']):
            return 'SATA HDD'
        elif '/dev/sd' in device_lower:
            return 'SATA Drive'
        else:
            return 'Unknown'
    
    def _format_storage_size(self, size_bytes: int) -> str:
        """Format storage size in human-readable format."""
        if size_bytes == 0:
            return "Unknown"
            
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}PB"


# Example usage and testing
async def test_list_nodes():
    """Test function to demonstrate list_nodes usage."""
    # This would use actual credentials from config
    client = ProxmoxAPIClient(
        host="192.168.10.200",
        username="root@pam",
        password="your_password",
        verify_ssl=False
    )
    
    # Authenticate
    if await client.authenticate():
        # List nodes
        nodes = await client.list_nodes()
        
        for node in nodes:
            print(f"Node: {node.node}")
            print(f"  Status: {node.status}")
            print(f"  CPU: {node.cpu:.1f}% of {node.maxcpu} cores")
            print(f"  Memory: {node.mem / (1024**3):.1f}GB of {node.maxmem / (1024**3):.1f}GB")
            print(f"  Disk: {node.disk / (1024**3):.1f}GB of {node.maxdisk / (1024**3):.1f}GB")
            print(f"  Uptime: {node.uptime // 86400} days")
            print()
    else:
        print("Authentication failed!")


if __name__ == "__main__":
    asyncio.run(test_list_nodes())