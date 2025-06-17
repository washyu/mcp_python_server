"""
LXD discovery tools for MCP server.
Provides container discovery, management, and deployment capabilities.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import asyncio

from ..utils.lxd_api import LXDAPIClient, LXDContainer
from ..utils.credential_manager import get_credential_manager

logger = logging.getLogger(__name__)


class LXDDiscoveryTools:
    """MCP tools for discovering and managing LXD containers."""
    
    def __init__(self):
        self.credential_manager = get_credential_manager()
        self._client: Optional[LXDAPIClient] = None
        
    async def _get_client(self) -> LXDAPIClient:
        """Get or create LXD API client."""
        if self._client is None:
            # Get credentials from secure storage
            creds = await self.credential_manager.get_credentials("lxd")
            if not creds:
                raise ValueError("LXD credentials not configured. Run 'setup-lxd' first.")
                
            self._client = LXDAPIClient(
                host=creds["host"],
                port=creds.get("port", 8443),
                ssh_user=creds.get("ssh_user"),
                ssh_port=creds.get("ssh_port", 22),
                verify_ssl=creds.get("verify_ssl", False)
            )
            await self._client.connect(method=creds.get("connection_method", "ssh"))
            
        return self._client
        
    async def list_containers(
        self,
        filter_by: Optional[str] = None,
        include_state: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List all LXD containers with optional filtering.
        
        Args:
            filter_by: Natural language filter (e.g., "running", "ubuntu", "web servers")
            include_state: Include runtime state information
            
        Returns:
            List of container information
        """
        try:
            client = await self._get_client()
            containers = await client.get_containers()
            
            result = []
            for container in containers:
                info = {
                    "name": container.get("name"),
                    "status": container.get("status"),
                    "architecture": container.get("architecture"),
                    "created_at": container.get("created_at"),
                    "profiles": container.get("profiles", []),
                    "config": container.get("config", {})
                }
                
                # Get runtime state if requested
                if include_state and container.get("status") == "Running":
                    try:
                        state = await client.get_container_state(container["name"])
                        info["cpu_usage"] = state.get("cpu", {}).get("usage", 0)
                        info["memory"] = {
                            "usage": state.get("memory", {}).get("usage", 0),
                            "limit": state.get("memory", {}).get("usage_peak", 0)
                        }
                        
                        # Extract IP addresses
                        info["ip_addresses"] = []
                        for iface_name, iface_data in state.get("network", {}).items():
                            for addr in iface_data.get("addresses", []):
                                if addr.get("family") == "inet" and not addr["address"].startswith("127."):
                                    info["ip_addresses"].append(addr["address"])
                    except Exception as e:
                        logger.warning(f"Failed to get state for {container['name']}: {e}")
                        
                # Apply filtering
                if filter_by:
                    filter_lower = filter_by.lower()
                    
                    # Status filter
                    if filter_lower in ["running", "stopped", "frozen"]:
                        if info["status"].lower() != filter_lower:
                            continue
                            
                    # Name filter
                    elif filter_lower in info["name"].lower():
                        pass  # Include this container
                        
                    # Architecture filter
                    elif filter_lower in ["arm", "arm64", "aarch64", "x86", "amd64"]:
                        if filter_lower not in info["architecture"].lower():
                            continue
                            
                    # Service type filter (based on name patterns)
                    elif any(svc in filter_lower for svc in ["web", "database", "db", "app", "api"]):
                        service_found = False
                        for svc in ["web", "database", "db", "app", "api"]:
                            if svc in filter_lower and svc in info["name"].lower():
                                service_found = True
                                break
                        if not service_found:
                            continue
                            
                result.append(info)
                
            return result
            
        except Exception as e:
            logger.error(f"Failed to list containers: {e}")
            raise
            
    async def discover_lxd_hosts(self) -> List[Dict[str, Any]]:
        """
        Discover available LXD hosts on the network.
        
        Returns:
            List of discovered LXD hosts
        """
        # For now, return configured host
        # In future, could implement network discovery
        try:
            creds = await self.credential_manager.get_credentials("lxd")
            if not creds:
                return []
                
            client = await self._get_client()
            server_info = await client.get_server_info()
            
            return [{
                "host": creds["host"],
                "port": creds.get("port", 8443),
                "api_version": server_info.get("api_version"),
                "server_version": server_info.get("server_version"),
                "architecture": server_info.get("architecture"),
                "clustered": len(await client.get_cluster_members()) > 1
            }]
            
        except Exception as e:
            logger.error(f"Failed to discover LXD hosts: {e}")
            return []
            
    async def get_container_details(self, name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific container.
        
        Args:
            name: Container name
            
        Returns:
            Detailed container information
        """
        try:
            client = await self._get_client()
            
            # Get container config
            container = await client.get_container_details(name)
            
            # Get runtime state
            state = None
            if container.get("status") == "Running":
                state = await client.get_container_state(name)
                
            return {
                "name": container.get("name"),
                "status": container.get("status"),
                "architecture": container.get("architecture"),
                "ephemeral": container.get("ephemeral", False),
                "profiles": container.get("profiles", []),
                "config": container.get("config", {}),
                "devices": container.get("devices", {}),
                "created_at": container.get("created_at"),
                "last_used_at": container.get("last_used_at"),
                "state": state
            }
            
        except Exception as e:
            logger.error(f"Failed to get container details: {e}")
            raise
            
    async def suggest_container_deployment(
        self,
        workload_type: str,
        requirements: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Suggest optimal container configuration for a workload.
        
        Args:
            workload_type: Type of workload (web, database, app, etc.)
            requirements: Optional specific requirements
            
        Returns:
            Deployment suggestion with configuration
        """
        try:
            client = await self._get_client()
            
            # Get current resource usage
            containers = await client.get_containers()
            running_count = sum(1 for c in containers if c.get("status") == "Running")
            
            # Get available images
            images = await client.get_images()
            
            # Base suggestions by workload type
            suggestions = {
                "web": {
                    "image": "ubuntu:22.04",
                    "cpu_limit": "2",
                    "memory_limit": "2GB",
                    "profiles": ["default"],
                    "devices": {
                        "eth0": {
                            "type": "nic",
                            "nictype": "bridged",
                            "parent": "lxdbr0"
                        }
                    }
                },
                "database": {
                    "image": "ubuntu:22.04",
                    "cpu_limit": "4",
                    "memory_limit": "4GB",
                    "profiles": ["default"],
                    "config": {
                        "security.privileged": "false",
                        "limits.cpu.priority": "10"
                    }
                },
                "app": {
                    "image": "ubuntu:22.04",
                    "cpu_limit": "2",
                    "memory_limit": "1GB",
                    "profiles": ["default"]
                },
                "development": {
                    "image": "ubuntu:22.04",
                    "cpu_limit": "2",
                    "memory_limit": "2GB",
                    "profiles": ["default"],
                    "config": {
                        "security.nesting": "true"  # Allow Docker inside LXD
                    }
                }
            }
            
            # Get base suggestion
            base = suggestions.get(workload_type.lower(), suggestions["app"])
            
            # Override with specific requirements
            if requirements:
                if "cpu" in requirements:
                    base["cpu_limit"] = str(requirements["cpu"])
                if "memory" in requirements:
                    base["memory_limit"] = requirements["memory"]
                if "image" in requirements:
                    base["image"] = requirements["image"]
                    
            # Check if suggested image is available
            image_available = any(
                img.get("properties", {}).get("os") in base["image"] 
                for img in images
            )
            
            return {
                "workload_type": workload_type,
                "suggested_config": base,
                "image_available": image_available,
                "current_container_count": len(containers),
                "running_container_count": running_count,
                "recommendation": f"Deploy {workload_type} container with {base['cpu_limit']} CPU cores and {base['memory_limit']} memory"
            }
            
        except Exception as e:
            logger.error(f"Failed to suggest deployment: {e}")
            raise
            
    async def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get overall resource usage across all containers.
        
        Returns:
            Resource usage summary
        """
        try:
            client = await self._get_client()
            
            # Get all containers
            containers = await client.get_containers()
            
            total_cpu = 0
            total_memory = 0
            container_stats = []
            
            for container in containers:
                if container.get("status") == "Running":
                    try:
                        state = await client.get_container_state(container["name"])
                        cpu_usage = state.get("cpu", {}).get("usage", 0)
                        memory_usage = state.get("memory", {}).get("usage", 0)
                        
                        total_cpu += cpu_usage
                        total_memory += memory_usage
                        
                        container_stats.append({
                            "name": container["name"],
                            "cpu_usage": cpu_usage,
                            "memory_usage": memory_usage
                        })
                    except Exception as e:
                        logger.warning(f"Failed to get stats for {container['name']}: {e}")
                        
            # Get storage pool info
            pools = await client.get_storage_pools()
            storage_info = []
            
            for pool in pools:
                try:
                    usage = await client.get_storage_pool_usage(pool["name"])
                    storage_info.append({
                        "name": pool["name"],
                        "driver": pool.get("driver"),
                        "used": usage.get("used", 0),
                        "total": usage.get("total", 0)
                    })
                except Exception as e:
                    logger.warning(f"Failed to get storage usage for {pool['name']}: {e}")
                    
            return {
                "container_count": len(containers),
                "running_containers": sum(1 for c in containers if c.get("status") == "Running"),
                "total_cpu_usage": total_cpu,
                "total_memory_usage": total_memory,
                "container_stats": container_stats,
                "storage_pools": storage_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get resource usage: {e}")
            raise
            
    async def generate_infrastructure_diagram(self) -> str:
        """
        Generate ASCII diagram of LXD infrastructure.
        
        Returns:
            ASCII art diagram
        """
        try:
            client = await self._get_client()
            
            # Get server info
            server_info = await client.get_server_info()
            host_info = (await self.discover_lxd_hosts())[0]
            
            # Get containers
            containers = await self.list_containers(include_state=True)
            
            # Build diagram
            diagram = []
            diagram.append("╔═══════════════════════════════════════════════════════════════╗")
            diagram.append(f"║ LXD Host: {host_info['host']}:{host_info['port']:<36} ║")
            diagram.append(f"║ Version: {server_info.get('server_version', 'Unknown'):<45} ║")
            diagram.append(f"║ Architecture: {server_info.get('architecture', 'Unknown'):<40} ║")
            diagram.append("╠═══════════════════════════════════════════════════════════════╣")
            diagram.append("║ Containers:                                                   ║")
            diagram.append("╟───────────────────────────────────────────────────────────────╢")
            
            if not containers:
                diagram.append("║ No containers found                                           ║")
            else:
                for container in containers:
                    status_icon = "●" if container["status"] == "Running" else "○"
                    name = container["name"][:20].ljust(20)
                    status = container["status"][:10].ljust(10)
                    
                    # Get IP if available
                    ip = "No IP"
                    if container.get("ip_addresses"):
                        ip = container["ip_addresses"][0]
                        
                    line = f"║ {status_icon} {name} {status} {ip:<20} ║"
                    diagram.append(line)
                    
            diagram.append("╚═══════════════════════════════════════════════════════════════╝")
            
            return "\n".join(diagram)
            
        except Exception as e:
            logger.error(f"Failed to generate diagram: {e}")
            raise
            
    async def close(self):
        """Close any open connections."""
        if self._client:
            await self._client.close()
            self._client = None


# Create singleton instance
_lxd_discovery_tools = None


def get_lxd_discovery_tools() -> LXDDiscoveryTools:
    """Get singleton instance of LXD discovery tools."""
    global _lxd_discovery_tools
    if _lxd_discovery_tools is None:
        _lxd_discovery_tools = LXDDiscoveryTools()
    return _lxd_discovery_tools