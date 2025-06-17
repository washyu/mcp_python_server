"""
LXD API client for managing containers on remote LXD hosts.
Supports SSH tunnel connections for secure remote management.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
import aiohttp
import asyncssh
from urllib.parse import quote

logger = logging.getLogger(__name__)


@dataclass
class LXDContainer:
    """Represents an LXD container."""
    name: str
    status: str
    architecture: str
    image: str
    cpu_usage: float = 0.0
    memory_usage: int = 0
    memory_limit: int = 0
    disk_usage: int = 0
    ipv4_addresses: List[str] = field(default_factory=list)
    profiles: List[str] = field(default_factory=list)
    created_at: Optional[str] = None
    last_used_at: Optional[str] = None


@dataclass
class LXDImage:
    """Represents an LXD image."""
    fingerprint: str
    alias: str
    architecture: str
    description: str
    size: int
    created_at: str
    auto_update: bool = False
    public: bool = False


@dataclass
class LXDNetwork:
    """Represents an LXD network."""
    name: str
    type: str
    bridge: Optional[str] = None
    ipv4_address: Optional[str] = None
    ipv4_cidr: Optional[str] = None
    dhcp_enabled: bool = False
    nat_enabled: bool = False


@dataclass
class LXDStoragePool:
    """Represents an LXD storage pool."""
    name: str
    driver: str
    used: int
    available: int
    total: int
    description: Optional[str] = None


class LXDAPIClient:
    """Client for interacting with LXD API via SSH tunnel or direct connection."""
    
    def __init__(
        self,
        host: str,
        port: int = 8443,
        ssh_user: Optional[str] = None,
        ssh_port: int = 22,
        verify_ssl: bool = False
    ):
        self.host = host
        self.port = port
        self.ssh_user = ssh_user
        self.ssh_port = ssh_port
        self.verify_ssl = verify_ssl
        self.base_url = f"https://localhost:{port}"
        self.session: Optional[aiohttp.ClientSession] = None
        self.ssh_tunnel: Optional[asyncssh.SSHTunnel] = None
        self.ssh_connection: Optional[asyncssh.SSHClientConnection] = None
        
    async def __aenter__(self):
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def connect(self, method: str = "ssh") -> bool:
        """Establish connection to LXD API."""
        if method == "ssh" and self.ssh_user:
            return await self.create_ssh_tunnel()
        elif method == "https":
            return await self.verify_ssl_certificate()
        elif method == "unix":
            return await self.test_unix_socket()
        else:
            raise ValueError(f"Unknown connection method: {method}")
            
    async def create_ssh_tunnel(self) -> bool:
        """Create SSH tunnel to access remote LXD API."""
        try:
            # Connect to remote host via SSH
            self.ssh_connection = await asyncssh.connect(
                self.host,
                port=self.ssh_port,
                username=self.ssh_user,
                known_hosts=None  # Accept any host key (consider security implications)
            )
            
            # Create tunnel from local port to remote LXD port
            self.ssh_tunnel = await self.ssh_connection.forward_local_port(
                "localhost", 0,  # Use any available local port
                "localhost", self.port
            )
            
            # Update base URL to use tunneled port
            local_port = self.ssh_tunnel.get_port()
            self.base_url = f"https://localhost:{local_port}"
            
            # Create aiohttp session
            connector = aiohttp.TCPConnector(ssl=False)
            self.session = aiohttp.ClientSession(connector=connector)
            
            # Test connection
            return await self.test_api_connection()
            
        except Exception as e:
            logger.error(f"Failed to create SSH tunnel: {e}")
            raise
            
    async def verify_ssl_certificate(self) -> bool:
        """Verify SSL certificate for direct HTTPS connection."""
        # For now, we'll skip SSL verification for self-signed certs
        connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
        self.session = aiohttp.ClientSession(connector=connector)
        self.base_url = f"https://{self.host}:{self.port}"
        return await self.test_api_connection()
        
    async def test_unix_socket(self) -> bool:
        """Test Unix socket connection for local LXD."""
        # Unix socket path for snap installation
        socket_path = "/var/snap/lxd/common/lxd/unix.socket"
        connector = aiohttp.UnixConnector(path=socket_path)
        self.session = aiohttp.ClientSession(connector=connector)
        self.base_url = "http://localhost"
        return await self.test_api_connection()
        
    async def test_api_connection(self) -> bool:
        """Test if API connection is working."""
        try:
            async with self.session.get(f"{self.base_url}/1.0") as resp:
                data = await resp.json()
                return data.get("metadata", {}).get("api_status") == "stable"
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return False
            
    async def close(self):
        """Close all connections."""
        if self.session:
            await self.session.close()
        if self.ssh_tunnel:
            self.ssh_tunnel.close()
        if self.ssh_connection:
            self.ssh_connection.close()
            
    async def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to LXD API."""
        if not self.session:
            raise RuntimeError("Not connected to LXD API")
            
        url = f"{self.base_url}{path}"
        async with self.session.request(method, url, **kwargs) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise Exception(f"LXD API error: {data.get('error', 'Unknown error')}")
            return data
            
    async def get_server_info(self) -> Dict[str, Any]:
        """Get LXD server information."""
        data = await self._request("GET", "/1.0")
        return data.get("metadata", {})
        
    async def get_containers(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all containers with optional status filter."""
        data = await self._request("GET", "/1.0/containers?recursion=1")
        containers = data.get("metadata", [])
        
        if status:
            containers = [c for c in containers if c.get("status") == status]
            
        return containers
        
    async def get_container_details(self, name: str) -> Dict[str, Any]:
        """Get detailed information about a specific container."""
        data = await self._request("GET", f"/1.0/containers/{quote(name)}")
        return data.get("metadata", {})
        
    async def get_container_state(self, name: str) -> Dict[str, Any]:
        """Get container runtime state information."""
        data = await self._request("GET", f"/1.0/containers/{quote(name)}/state")
        return data.get("metadata", {})
        
    async def create_container(
        self,
        name: str,
        image: str,
        profiles: List[str] = None,
        config: Dict[str, str] = None,
        devices: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a new container."""
        if profiles is None:
            profiles = ["default"]
            
        payload = {
            "name": name,
            "source": {
                "type": "image",
                "alias": image
            },
            "profiles": profiles
        }
        
        if config:
            payload["config"] = config
        if devices:
            payload["devices"] = devices
            
        data = await self._request("POST", "/1.0/containers", json=payload)
        return data.get("metadata", {})
        
    async def start_container(self, name: str) -> Dict[str, Any]:
        """Start a container."""
        payload = {"action": "start"}
        data = await self._request("PUT", f"/1.0/containers/{quote(name)}/state", json=payload)
        return data.get("metadata", {})
        
    async def stop_container(self, name: str, force: bool = False) -> Dict[str, Any]:
        """Stop a container."""
        payload = {"action": "stop", "force": force}
        data = await self._request("PUT", f"/1.0/containers/{quote(name)}/state", json=payload)
        return data.get("metadata", {})
        
    async def delete_container(self, name: str) -> Dict[str, Any]:
        """Delete a container."""
        data = await self._request("DELETE", f"/1.0/containers/{quote(name)}")
        return data.get("metadata", {})
        
    async def get_images(self) -> List[Dict[str, Any]]:
        """List all available images."""
        data = await self._request("GET", "/1.0/images?recursion=1")
        return data.get("metadata", [])
        
    async def download_image(self, alias: str, remote: str = "images") -> Dict[str, Any]:
        """Download an image from a remote repository."""
        payload = {
            "source": {
                "type": "image",
                "mode": "pull",
                "server": f"https://{remote}.linuxcontainers.org",
                "alias": alias
            }
        }
        data = await self._request("POST", "/1.0/images", json=payload)
        return data.get("metadata", {})
        
    async def get_networks(self) -> List[Dict[str, Any]]:
        """List all networks."""
        data = await self._request("GET", "/1.0/networks?recursion=1")
        return data.get("metadata", [])
        
    async def create_network(self, name: str, type: str = "bridge", config: Dict[str, str] = None) -> Dict[str, Any]:
        """Create a new network."""
        payload = {
            "name": name,
            "type": type
        }
        if config:
            payload["config"] = config
            
        data = await self._request("POST", "/1.0/networks", json=payload)
        return data.get("metadata", {})
        
    async def get_storage_pools(self) -> List[Dict[str, Any]]:
        """List all storage pools."""
        data = await self._request("GET", "/1.0/storage-pools?recursion=1")
        return data.get("metadata", [])
        
    async def get_storage_pool_usage(self, name: str) -> Dict[str, Any]:
        """Get storage pool usage statistics."""
        data = await self._request("GET", f"/1.0/storage-pools/{quote(name)}/resources")
        return data.get("metadata", {})
        
    async def get_cluster_members(self) -> List[Dict[str, Any]]:
        """Get cluster member information."""
        try:
            data = await self._request("GET", "/1.0/cluster/members?recursion=1")
            return data.get("metadata", [])
        except Exception:
            # Not a clustered LXD instance
            return []
            
    async def get_container_logs(self, name: str, lines: int = 100) -> str:
        """Get container console logs."""
        # LXD doesn't have a direct log endpoint, this would need to exec into container
        # For now, return placeholder
        return f"Container {name} logs would be retrieved here"
        
    async def exec_in_container(self, name: str, command: List[str]) -> Dict[str, Any]:
        """Execute a command inside a container."""
        payload = {
            "command": command,
            "wait-for-websocket": False,
            "interactive": False
        }
        data = await self._request("POST", f"/1.0/containers/{quote(name)}/exec", json=payload)
        return data.get("metadata", {})