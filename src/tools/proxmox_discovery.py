"""
MCP tools for Proxmox discovery operations.
"""

from typing import Dict, Any, List, Optional
from mcp import Tool
from mcp.types import TextContent
import logging
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from src.utils.proxmox_api import ProxmoxAPIClient, ProxmoxNode
from src.utils.credential_manager import get_credential_manager
from src.utils.config import Config

logger = logging.getLogger(__name__)


class ProxmoxDiscoveryTools:
    """Collection of Proxmox discovery tools for MCP."""
    
    def __init__(self, credential_manager=None):
        """Initialize discovery tools with Proxmox configuration."""
        self.credential_manager = credential_manager or get_credential_manager()
        self.api_client = None
        self.inventory_dir = Path("inventory")
        self.inventory_dir.mkdir(exist_ok=True)
        
        # Inventory files
        self.resources_file = self.inventory_dir / "proxmox-resources.json"
        self.discovery_file = self.inventory_dir / "last-discovery.json"
        
        # Staleness threshold (configurable)
        self.staleness_hours = int(getattr(Config, 'INVENTORY_STALENESS_HOURS', 10))
    
    async def _get_api_client(self) -> ProxmoxAPIClient:
        """Get authenticated Proxmox API client."""
        if self.api_client is None:
            # Get credentials from credential manager
            creds = await self.credential_manager.get_service_credentials("proxmox")
            
            # If missing keys, try to get from profile manager as fallback
            if not creds or "host" not in creds:
                try:
                    from src.utils.profile_manager import ProfileManager
                    pm = ProfileManager()
                    profile = await pm.get_profile("main")
                    if profile:
                        # Map profile keys to expected keys
                        creds = {
                            "host": profile.get("PROXMOX_HOST"),
                            "username": profile.get("PROXMOX_USER"), 
                            "password": profile.get("PROXMOX_PASSWORD"),
                            "api_token": profile.get("PROXMOX_API_TOKEN"),
                            "verify_ssl": profile.get("PROXMOX_VERIFY_SSL", "false").lower() == "true"
                        }
                        
                        # Merge with credential manager data (only if it has real values, not placeholders)
                        cm_creds = await self.credential_manager.get_service_credentials("proxmox")
                        if cm_creds:
                            # Only merge non-placeholder values
                            for key, value in cm_creds.items():
                                if value and value not in ['your_password_here', 'your_token_here']:
                                    creds[key] = value
                except Exception as e:
                    logger.warning(f"Failed to load profile credentials: {e}")
            
            if not creds or not creds.get("host"):
                raise ValueError("No Proxmox credentials found. Please run setup wizard first.")
            
            # Create API client (prefer password auth for reliability)
            if "username" in creds and "password" in creds:
                self.api_client = ProxmoxAPIClient(
                    host=creds["host"],
                    username=creds["username"],
                    password=creds["password"],
                    verify_ssl=creds.get("verify_ssl", False)
                )
            elif "api_token" in creds and creds["api_token"]:
                self.api_client = ProxmoxAPIClient(
                    host=creds["host"],
                    api_token=creds["api_token"],
                    verify_ssl=creds.get("verify_ssl", False)
                )
            else:
                raise ValueError("Invalid Proxmox credentials. Need either API token or username/password.")
            
            # Authenticate
            success = await self.api_client.authenticate()
            if not success:
                raise ValueError("Failed to authenticate with Proxmox server")
        
        return self.api_client
    
    async def _is_inventory_stale(self) -> bool:
        """Check if inventory is stale and needs refresh."""
        if not self.discovery_file.exists():
            return True
        
        try:
            with open(self.discovery_file, 'r') as f:
                discovery_data = json.load(f)
            
            last_update = datetime.fromisoformat(discovery_data.get("last_update", "1970-01-01"))
            threshold = datetime.now() - timedelta(hours=self.staleness_hours)
            
            return last_update < threshold
        except (json.JSONDecodeError, KeyError, ValueError):
            return True
    
    async def _save_inventory(self, inventory: Dict[str, Any]) -> None:
        """Save inventory to JSON file with timestamp."""
        # Save resources
        with open(self.resources_file, 'w') as f:
            json.dump(inventory, f, indent=2, default=str)
        
        # Update discovery metadata
        discovery_data = {
            "last_update": datetime.now().isoformat(),
            "staleness_hours": self.staleness_hours,
            "resource_count": {
                "nodes": len(inventory.get("nodes", [])),
                "vms": len(inventory.get("vms", [])),
                "storage": len(inventory.get("storage", [])),
                "networks": len(inventory.get("networks", [])),
                "templates": len(inventory.get("templates", []))
            }
        }
        
        with open(self.discovery_file, 'w') as f:
            json.dump(discovery_data, f, indent=2)
        
        logger.info(f"Inventory saved with {sum(discovery_data['resource_count'].values())} total resources")
    
    async def _load_inventory(self) -> Optional[Dict[str, Any]]:
        """Load inventory from JSON file."""
        if not self.resources_file.exists():
            return None
        
        try:
            with open(self.resources_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None
    
    async def refresh_inventory(self, include_hardware: bool = True) -> Dict[str, Any]:
        """Refresh complete Proxmox inventory with optional hardware discovery."""
        logger.info("Refreshing Proxmox inventory...")
        
        try:
            client = await self._get_api_client()
            
            # Discover all resources in parallel
            tasks = {
                "nodes": client.list_nodes(),
                "vms": client.list_vms(),
                "storage": client.list_storage(),
                "networks": client.list_networks(),
                "templates": client.list_templates()
            }
            
            # Execute all discovery tasks
            results = {}
            for resource_type, task in tasks.items():
                try:
                    results[resource_type] = await task
                    logger.info(f"Discovered {len(results[resource_type])} {resource_type}")
                except Exception as e:
                    logger.error(f"Failed to discover {resource_type}: {e}")
                    results[resource_type] = []
            
            # Enhanced hardware discovery for nodes
            if include_hardware and results.get("nodes"):
                logger.info("Discovering detailed hardware information...")
                for i, node in enumerate(results["nodes"]):
                    try:
                        if hasattr(node, 'node'):
                            node_name = node.node
                        else:
                            # Handle string representation
                            import re
                            match = re.search(r"node='([^']*)'?", str(node))
                            node_name = match.group(1) if match else "unknown"
                        
                        hardware = await client.discover_node_hardware(node_name)
                        
                        # Update node with hardware info
                        if hasattr(node, 'hardware'):
                            node.hardware = hardware
                        else:
                            # For dict-based nodes, add hardware field
                            if isinstance(results["nodes"][i], dict):
                                results["nodes"][i]["hardware"] = hardware
                            
                        logger.info(f"Hardware discovered for {node_name}: {len(hardware.gpus)} GPUs, "
                                  f"{len(hardware.storage_devices)} storage devices")
                                  
                    except Exception as e:
                        logger.warning(f"Failed to discover hardware for node {node_name}: {e}")
            
            # Add metadata
            inventory = {
                **results,
                "discovery_time": datetime.now().isoformat(),
                "proxmox_host": client.host,
                "total_resources": sum(len(v) for v in results.values())
            }
            
            # Save inventory
            await self._save_inventory(inventory)
            
            return inventory
            
        except Exception as e:
            logger.error(f"Failed to refresh inventory: {e}")
            raise
    
    async def get_inventory(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get inventory, refreshing if stale or forced."""
        if force_refresh or await self._is_inventory_stale():
            return await self.refresh_inventory()
        else:
            inventory = await self._load_inventory()
            if inventory is None:
                return await self.refresh_inventory()
            return inventory
    
    # MCP Tool implementations
    
    async def list_nodes(self) -> List[TextContent]:
        """List all Proxmox nodes."""
        try:
            inventory = await self.get_inventory()
            nodes = inventory.get("nodes", [])
            
            if not nodes:
                return [TextContent(
                    type="text",
                    text="No Proxmox nodes found. This might indicate a connection issue."
                )]
            
            # Format nodes for display
            result = ["📟 **Proxmox Nodes**\n"]
            for node in nodes:
                if isinstance(node, dict):
                    name = node.get("node", "Unknown")
                    status = node.get("status", "unknown")
                    cpu_pct = f"{node.get('cpu', 0) * 100:.1f}%"
                    mem_used = node.get('mem', 0) / (1024**3)  # Convert to GB
                    mem_total = node.get('maxmem', 0) / (1024**3)
                    
                    status_emoji = "🟢" if status == "online" else "🔴"
                    
                    result.append(f"{status_emoji} **{name}** ({status})")
                    result.append(f"  CPU: {cpu_pct}, Memory: {mem_used:.1f}GB / {mem_total:.1f}GB")
                elif isinstance(node, str):
                    # Handle string representation of ProxmoxNode (parse it)
                    try:
                        # Extract values from string like "ProxmoxNode(node='proxmox', status='online', ...)"
                        import re
                        
                        node_match = re.search(r"node='([^']*)'", node)
                        status_match = re.search(r"status='([^']*)'", node)
                        cpu_match = re.search(r"cpu=([0-9.]+)", node)
                        mem_match = re.search(r"mem=([0-9]+)", node)
                        maxmem_match = re.search(r"maxmem=([0-9]+)", node)
                        
                        name = node_match.group(1) if node_match else "Unknown"
                        status = status_match.group(1) if status_match else "unknown"
                        cpu = float(cpu_match.group(1)) if cpu_match else 0.0
                        mem = int(mem_match.group(1)) if mem_match else 0
                        maxmem = int(maxmem_match.group(1)) if maxmem_match else 0
                        
                        cpu_pct = f"{cpu * 100:.1f}%"
                        mem_used = mem / (1024**3)  # Convert to GB
                        mem_total = maxmem / (1024**3)
                        
                        status_emoji = "🟢" if status == "online" else "🔴"
                        
                        result.append(f"{status_emoji} **{name}** ({status})")
                        result.append(f"  CPU: {cpu_pct}, Memory: {mem_used:.1f}GB / {mem_total:.1f}GB")
                    except Exception as e:
                        logger.warning(f"Failed to parse node string: {e}")
                        result.append(f"❓ **Node** (parse error)")
                else:
                    # Handle ProxmoxNode object
                    try:
                        status_emoji = "🟢" if node.status == "online" else "🔴"
                        cpu_pct = f"{node.cpu * 100:.1f}%"
                        mem_used = node.mem / (1024**3)
                        mem_total = node.maxmem / (1024**3)
                        
                        result.append(f"{status_emoji} **{node.node}** ({node.status})")
                        result.append(f"  CPU: {cpu_pct}, Memory: {mem_used:.1f}GB / {mem_total:.1f}GB")
                    except Exception as e:
                        logger.warning(f"Failed to parse node object: {e}")
                        result.append(f"❓ **Node** (object error)")
            
            return [TextContent(type="text", text="\n".join(result))]
            
        except Exception as e:
            logger.error(f"Failed to list nodes: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Error listing nodes: {e}"
            )]
    
    async def list_vms(self, filters: Dict[str, Any] = None) -> List[TextContent]:
        """List all virtual machines with comprehensive filtering support."""
        try:
            inventory = await self.get_inventory()
            vms = inventory.get("vms", [])
            
            if not vms:
                return [TextContent(
                    type="text",
                    text="No virtual machines found."
                )]
            
            # Apply filters if provided
            filtered_vms = vms
            filter_descriptions = []
            
            # Smart detection for obviously nonsensical queries
            # If no filters were detected, check if this seems like a legitimate "list all" vs nonsensical query
            if filters is not None and len(filters) == 0:
                # For now, we'll allow empty filters (legitimate "list all vms")
                # Future enhancement: Could add nonsensical keyword detection here
                pass
            
            if filters:
                # Status filter
                if filters.get("status"):
                    status = filters["status"].lower()
                    filtered_vms = [vm for vm in filtered_vms if vm.get("status", "").lower() == status]
                    filter_descriptions.append(f"status: {status}")
                
                # Name filter (contains)
                if filters.get("name"):
                    name_filter = filters["name"].lower()
                    filtered_vms = [vm for vm in filtered_vms 
                                  if name_filter in vm.get("name", "").lower()]
                    filter_descriptions.append(f"name contains: {name_filter}")
                
                # ID filter (exact match)
                if filters.get("id"):
                    vm_id = filters["id"]
                    # Handle both string and int IDs
                    if isinstance(vm_id, str) and vm_id.isdigit():
                        vm_id = int(vm_id)
                    filtered_vms = [vm for vm in filtered_vms if vm.get("vmid") == vm_id]
                    filter_descriptions.append(f"ID: {vm_id}")
                
                # OS/Distribution filter (check tags and name)
                if filters.get("os"):
                    os_filter = filters["os"].lower()
                    filtered_vms = [vm for vm in filtered_vms 
                                  if self._matches_os_filter(vm, os_filter)]
                    filter_descriptions.append(f"OS: {os_filter}")
                
                # Node filter
                if filters.get("node"):
                    node_filter = filters["node"].lower()
                    filtered_vms = [vm for vm in filtered_vms 
                                  if node_filter in vm.get("node", "").lower()]
                    filter_descriptions.append(f"node: {node_filter}")
                
                # Memory filter (greater than or equal to specified MB)
                if filters.get("min_memory"):
                    min_mem_mb = filters["min_memory"]
                    min_mem_bytes = min_mem_mb * 1024 * 1024  # Convert MB to bytes
                    filtered_vms = [vm for vm in filtered_vms 
                                  if vm.get("maxmem", 0) >= min_mem_bytes]
                    # Display in GB if >= 1024MB for better readability
                    if min_mem_mb >= 1024:
                        filter_descriptions.append(f"memory >= {min_mem_mb / 1024:.1f}GB")
                    else:
                        filter_descriptions.append(f"memory >= {min_mem_mb}MB")
                
                # CPU filter (greater than specified cores)
                if filters.get("min_cpu"):
                    min_cpu = filters["min_cpu"]
                    filtered_vms = [vm for vm in filtered_vms 
                                  if vm.get("cpus", 0) >= min_cpu]
                    filter_descriptions.append(f"CPU >= {min_cpu} cores")
            
            if not filtered_vms:
                filter_desc = ", ".join(filter_descriptions) if filter_descriptions else "specified criteria"
                return [TextContent(
                    type="text",
                    text=f"No virtual machines found matching {filter_desc}."
                )]
            
            # Format VMs for display
            title = f"🖥️ **Virtual Machines"
            if filter_descriptions:
                title += f" ({', '.join(filter_descriptions)})"
            title += f"** ({len(filtered_vms)} found)\n"
            
            result = [title]
            for vm in filtered_vms:
                vm_id = vm.get("vmid", "?")
                name = vm.get("name", "Unknown")
                status = vm.get("status", "unknown")
                node = vm.get("node", "unknown")
                
                status_emoji = {
                    "running": "🟢",
                    "stopped": "🔴", 
                    "paused": "⏸️"
                }.get(status, "❓")
                
                result.append(f"{status_emoji} **{name}** (ID: {vm_id}) on {node}")
                result.append(f"  Status: {status}")
                
                # Show additional details
                if "cpus" in vm:
                    result.append(f"  CPU: {vm['cpus']} cores, Memory: {vm.get('maxmem', 0) / (1024**3):.1f}GB")
                
                # Show tags if available
                if vm.get("tags"):
                    tags = vm["tags"].split(";")[:3]  # Show first 3 tags
                    result.append(f"  Tags: {', '.join(tags)}")
            
            return [TextContent(type="text", text="\n".join(result))]
            
        except Exception as e:
            logger.error(f"Failed to list VMs: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Error listing VMs: {e}"
            )]
    
    def _matches_os_filter(self, vm: Dict[str, Any], os_filter: str) -> bool:
        """Check if VM matches OS filter by checking name and tags with comprehensive patterns."""
        name = vm.get("name", "").lower()
        tags = vm.get("tags", "").lower()
        
        # Expanded OS patterns with regex support
        import re
        os_patterns = {
            # Version-specific patterns (priority matches)
            "ubuntu 22.04": [r"ubuntu.*22\.?04", r"jammy", r"22\.04"],
            "ubuntu 20.04": [r"ubuntu.*20\.?04", r"focal", r"20\.04"], 
            "ubuntu 18.04": [r"ubuntu.*18\.?04", r"bionic", r"18\.04"],
            "windows server 2022": [r"windows.*2022", r"w2k22", r"ws2022", r"server.*2022"],
            "windows server 2019": [r"windows.*2019", r"w2k19", r"ws2019", r"server.*2019"],
            # General OS patterns
            "windows": [r"windows", r"win(?!g)", r"w2k", r"server.*20\d{2}"],
            "ubuntu": [r"ubuntu(?!\s*\d)"],  # Ubuntu without version
            "debian": [r"debian"],
            "centos": [r"centos", r"rhel", r"redhat", r"rocky", r"alma"],
            "linux": [r"ubuntu", r"debian", r"centos", r"rhel", r"linux", r"rocky", r"alma"],
            # Service-based detection
            "nextcloud": [r"nextcloud"],
            "docker": [r"docker", r"container"],
            "mysql": [r"mysql", r"mariadb", r"database(?!\s*server)", r"\bdb\b"],
            "web": [r"web.*server", r"nginx", r"apache", r"httpd"],
            "database": [r"database", r"db.*server", r"postgres", r"mongodb", r"mysql", r"mariadb"],
            # Environment patterns
            "production": [r"production", r"prod(?!\s*server)"],
            "development": [r"development", r"dev(?!\s*server)"],
            "test": [r"test(?!\s*server)", r"testing", r"staging"]
        }
        
        # Check direct matches first
        if os_filter in name or os_filter in tags:
            return True
        
        # Check regex pattern matches
        if os_filter in os_patterns:
            patterns = os_patterns[os_filter]
            for pattern in patterns:
                if re.search(pattern, name) or re.search(pattern, tags):
                    return True
        
        # Fallback: simple substring matching for unlisted filters
        return os_filter in name or os_filter in tags
    
    async def discover_hardware(self, node_name: str = None) -> List[TextContent]:
        """Discover detailed hardware capabilities of nodes."""
        try:
            client = await self._get_api_client()
            inventory = await self.get_inventory()
            nodes = inventory.get("nodes", [])
            
            if not nodes:
                return [TextContent(
                    type="text",
                    text="No nodes found to discover hardware for."
                )]
            
            # Filter to specific node if requested
            if node_name:
                target_nodes = []
                for node in nodes:
                    if hasattr(node, 'node'):
                        if node.node == node_name:
                            target_nodes = [node]
                            break
                    else:
                        # Handle string representation
                        import re
                        match = re.search(r"node='([^']*)'?", str(node))
                        if match and match.group(1) == node_name:
                            target_nodes = [node]
                            break
                
                if not target_nodes:
                    return [TextContent(
                        type="text",
                        text=f"❌ Node '{node_name}' not found."
                    )]
                nodes = target_nodes
            
            result = ["🔧 **Hardware Discovery**\n"]
            
            for node in nodes:
                try:
                    # Get node name
                    if hasattr(node, 'node'):
                        current_node_name = node.node
                    else:
                        import re
                        match = re.search(r"node='([^']*)'?", str(node))
                        current_node_name = match.group(1) if match else "unknown"
                    
                    # Discover hardware for this node
                    hardware = await client.discover_node_hardware(current_node_name)
                    
                    result.append(f"🖥️ **{current_node_name}**")
                    
                    # GPUs
                    if hardware.gpus:
                        result.append(f"  🎮 **GPUs ({len(hardware.gpus)}):**")
                        for gpu in hardware.gpus:
                            capabilities = ", ".join(gpu.suitable_for) if gpu.suitable_for else "general"
                            result.append(f"    • {gpu.model}")
                            result.append(f"      Capabilities: {capabilities}")
                            if gpu.memory:
                                result.append(f"      Memory: {gpu.memory}")
                    else:
                        result.append("  🎮 **GPUs:** None detected")
                    
                    # CPU
                    if hardware.cpu_details:
                        cpu = hardware.cpu_details
                        result.append(f"  ⚡ **CPU:** {cpu.model}")
                        result.append(f"    Cores: {cpu.cores}, Threads: {cpu.threads}")
                        if cpu.frequency:
                            result.append(f"    Frequency: {cpu.frequency}")
                        if cpu.features:
                            result.append(f"    Features: {', '.join(cpu.features[:5])}")
                    
                    # Storage
                    if hardware.storage_devices:
                        result.append(f"  💾 **Storage ({len(hardware.storage_devices)}):**")
                        for storage in hardware.storage_devices:
                            result.append(f"    • {storage.model} ({storage.type}) - {storage.size}")
                    
                    result.append("")  # Empty line between nodes
                    
                except Exception as e:
                    result.append(f"❌ Failed to discover hardware for {current_node_name}: {e}")
                    result.append("")
            
            return [TextContent(type="text", text="\n".join(result))]
            
        except Exception as e:
            logger.error(f"Failed to discover hardware: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Error discovering hardware: {e}"
            )]
    
    async def suggest_deployment(self, workload_type: str, requirements: dict = None) -> List[TextContent]:
        """Get AI-powered deployment suggestions based on hardware capabilities."""
        try:
            inventory = await self.get_inventory()
            nodes = inventory.get("nodes", [])
            
            if not nodes:
                return [TextContent(
                    type="text",
                    text="No nodes available for deployment."
                )]
            
            # Define workload profiles
            workload_profiles = {
                "ai_training": {
                    "requires_gpu": True,
                    "min_cpu": 4,
                    "min_memory_gb": 16,
                    "preferred_storage": "nvme",
                    "description": "AI/ML training workload"
                },
                "database": {
                    "requires_gpu": False,
                    "min_cpu": 4,
                    "min_memory_gb": 8,
                    "preferred_storage": "nvme",
                    "description": "Database server"
                },
                "web_server": {
                    "requires_gpu": False,
                    "min_cpu": 2,
                    "min_memory_gb": 4,
                    "preferred_storage": "ssd",
                    "description": "Web application server"
                },
                "compute": {
                    "requires_gpu": False,
                    "min_cpu": 8,
                    "min_memory_gb": 16,
                    "preferred_storage": "any",
                    "description": "General compute workload"
                },
                "storage": {
                    "requires_gpu": False,
                    "min_cpu": 2,
                    "min_memory_gb": 4,
                    "preferred_storage": "hdd",
                    "description": "Storage/backup server"
                },
                "general": {
                    "requires_gpu": False,
                    "min_cpu": 2,
                    "min_memory_gb": 2,
                    "preferred_storage": "any",
                    "description": "General purpose VM"
                }
            }
            
            profile = workload_profiles.get(workload_type, workload_profiles["general"])
            
            # Override with user requirements
            if requirements:
                profile.update(requirements)
            
            result = [f"🎯 **Deployment Suggestions for {workload_type.title()}**\n"]
            result.append(f"Requirements: {profile['description']}")
            result.append(f"  • CPU: {profile.get('min_cpu', 2)}+ cores")
            result.append(f"  • Memory: {profile.get('min_memory_gb', 2)}+ GB")
            result.append(f"  • GPU: {'Required' if profile.get('requires_gpu') else 'Optional'}")
            result.append(f"  • Storage: {profile.get('preferred_storage', 'any').upper()}\n")
            
            scored_nodes = []
            
            for node in nodes:
                score = 0
                reasons = []
                warnings = []
                
                # Get node name and basic stats
                if hasattr(node, 'node'):
                    node_name = node.node
                    max_cpu = getattr(node, 'maxcpu', 0)
                    max_mem_gb = getattr(node, 'maxmem', 0) / (1024**3)
                    current_cpu = getattr(node, 'cpu', 0) * 100
                    current_mem_gb = getattr(node, 'mem', 0) / (1024**3)
                    hardware = getattr(node, 'hardware', None)
                else:
                    # Handle string representation (fallback)
                    import re
                    match = re.search(r"node='([^']*)'", str(node))
                    node_name = match.group(1) if match else "unknown"
                    max_cpu = max_mem_gb = current_cpu = current_mem_gb = 0
                    hardware = None
                
                # Check basic requirements
                available_cpu = max_cpu
                available_mem_gb = max_mem_gb - current_mem_gb
                
                if available_cpu >= profile.get("min_cpu", 2):
                    score += 50
                    reasons.append(f"Sufficient CPU ({available_cpu} cores available)")
                else:
                    score -= 100
                    warnings.append(f"Insufficient CPU ({available_cpu} < {profile.get('min_cpu', 2)})")
                
                if available_mem_gb >= profile.get("min_memory_gb", 2):
                    score += 50
                    reasons.append(f"Sufficient memory ({available_mem_gb:.1f}GB available)")
                else:
                    score -= 100
                    warnings.append(f"Insufficient memory ({available_mem_gb:.1f}GB < {profile.get('min_memory_gb', 2)}GB)")
                
                # Check GPU requirements
                if profile.get("requires_gpu"):
                    if hardware and hardware.gpus:
                        ai_gpus = [gpu for gpu in hardware.gpus if "ai_training" in gpu.suitable_for]
                        if ai_gpus:
                            score += 100
                            reasons.append(f"Has AI-capable GPU: {ai_gpus[0].model}")
                        else:
                            score += 30
                            reasons.append(f"Has GPU: {hardware.gpus[0].model}")
                    else:
                        score -= 200
                        warnings.append("No GPU detected (required for AI training)")
                
                # Check storage preferences
                if hardware and hardware.storage_devices:
                    nvme_count = len([s for s in hardware.storage_devices if "nvme" in s.type.lower()])
                    ssd_count = len([s for s in hardware.storage_devices if "ssd" in s.type.lower()])
                    
                    preferred = profile.get("preferred_storage", "any")
                    if preferred == "nvme" and nvme_count > 0:
                        score += 30
                        reasons.append(f"Has {nvme_count} NVMe drive(s)")
                    elif preferred == "ssd" and (nvme_count > 0 or ssd_count > 0):
                        score += 20
                        reasons.append(f"Has fast storage ({nvme_count + ssd_count} SSD/NVMe)")
                
                # Utilization bonus (prefer less loaded nodes)
                if current_cpu < 50:
                    score += 20
                    reasons.append(f"Low CPU utilization ({current_cpu:.1f}%)")
                elif current_cpu > 80:
                    score -= 30
                    warnings.append(f"High CPU utilization ({current_cpu:.1f}%)")
                
                scored_nodes.append({
                    "node": node_name,
                    "score": score,
                    "reasons": reasons,
                    "warnings": warnings
                })
            
            # Sort by score
            scored_nodes.sort(key=lambda x: x["score"], reverse=True)
            
            # Display recommendations
            for i, node_info in enumerate(scored_nodes[:3]):  # Top 3 recommendations
                rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else "📍"
                recommendation = "✅ **RECOMMENDED**" if node_info["score"] > 0 else "❌ **NOT SUITABLE**"
                
                result.append(f"{rank_emoji} **{node_info['node']}** (Score: {node_info['score']}) {recommendation}")
                
                for reason in node_info["reasons"]:
                    result.append(f"  ✅ {reason}")
                
                for warning in node_info["warnings"]:
                    result.append(f"  ⚠️ {warning}")
                
                result.append("")
            
            return [TextContent(type="text", text="\n".join(result))]
            
        except Exception as e:
            logger.error(f"Failed to suggest deployment: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Error generating deployment suggestions: {e}"
            )]
    
    async def optimize_placement(self) -> List[TextContent]:
        """Analyze current VM placement and suggest optimizations."""
        try:
            inventory = await self.get_inventory()
            nodes = inventory.get("nodes", [])
            vms = inventory.get("vms", [])
            
            if not nodes or not vms:
                return [TextContent(
                    type="text",
                    text="Insufficient data for placement optimization analysis."
                )]
            
            result = ["⚖️ **VM Placement Optimization Analysis**\n"]
            
            # Analyze current utilization by node
            node_analysis = {}
            
            for node in nodes:
                if hasattr(node, 'node'):
                    node_name = node.node
                    cpu_usage = getattr(node, 'cpu', 0) * 100
                    mem_usage = (getattr(node, 'mem', 0) / getattr(node, 'maxmem', 1)) * 100
                    max_cpu = getattr(node, 'maxcpu', 0)
                    max_mem_gb = getattr(node, 'maxmem', 0) / (1024**3)
                    hardware = getattr(node, 'hardware', None)
                else:
                    continue  # Skip string representations for now
                
                # Count VMs on this node
                node_vms = [vm for vm in vms if vm.get("node") == node_name]
                
                node_analysis[node_name] = {
                    "cpu_usage": cpu_usage,
                    "mem_usage": mem_usage,
                    "max_cpu": max_cpu,
                    "max_mem_gb": max_mem_gb,
                    "vm_count": len(node_vms),
                    "vms": node_vms,
                    "hardware": hardware
                }
            
            # Display current state
            result.append("**Current Node Utilization:**")
            overloaded_nodes = []
            underutilized_nodes = []
            
            for node_name, stats in node_analysis.items():
                status_emoji = "🟢"
                status = "Optimal"
                
                if stats["cpu_usage"] > 80 or stats["mem_usage"] > 80:
                    status_emoji = "🔴"
                    status = "Overloaded"
                    overloaded_nodes.append((node_name, stats))
                elif stats["cpu_usage"] < 30 and stats["mem_usage"] < 30:
                    status_emoji = "🟡"  
                    status = "Underutilized"
                    underutilized_nodes.append((node_name, stats))
                
                result.append(f"{status_emoji} **{node_name}** ({status})")
                result.append(f"  CPU: {stats['cpu_usage']:.1f}%, Memory: {stats['mem_usage']:.1f}%")
                result.append(f"  VMs: {stats['vm_count']}")
                
                # Show GPU allocation if available
                if stats["hardware"] and stats["hardware"].gpus:
                    gpu_vms = [vm for vm in stats["vms"] if "ollama" in vm.get("name", "").lower() or "ai" in vm.get("name", "").lower()]
                    if gpu_vms:
                        result.append(f"  GPU Usage: {len(gpu_vms)} AI VM(s)")
                    else:
                        result.append(f"  GPU Usage: Available ({len(stats['hardware'].gpus)} GPU(s))")
                
                result.append("")
            
            # Generate optimization suggestions
            suggestions = []
            
            # Check for VMs that could be migrated from overloaded to underutilized nodes
            for overloaded_node, overloaded_stats in overloaded_nodes:
                for vm in overloaded_stats["vms"]:
                    if vm.get("status") != "running":
                        continue  # Skip stopped VMs
                    
                    vm_name = vm.get("name", "Unknown")
                    vm_cpu = vm.get("cpus", 0)
                    vm_mem_gb = vm.get("maxmem", 0) / (1024**3)
                    
                    # Check if VM needs GPU
                    needs_gpu = any(keyword in vm_name.lower() for keyword in ["ollama", "ai", "cuda", "rocm"])
                    
                    # Find suitable target nodes
                    for underutil_node, underutil_stats in underutilized_nodes:
                        # Check if target node has capacity
                        if (underutil_stats["max_cpu"] >= vm_cpu and 
                            underutil_stats["max_mem_gb"] >= vm_mem_gb):
                            
                            # Check GPU requirement
                            if needs_gpu:
                                if not (underutil_stats["hardware"] and underutil_stats["hardware"].gpus):
                                    continue  # Skip if GPU needed but not available
                            
                            benefit = "Free up resources on overloaded node"
                            if needs_gpu and underutil_stats["hardware"] and underutil_stats["hardware"].gpus:
                                benefit += " and utilize available GPU"
                            
                            suggestions.append({
                                "action": f"Migrate '{vm_name}' from {overloaded_node} to {underutil_node}",
                                "benefit": benefit,
                                "priority": "High" if overloaded_stats["cpu_usage"] > 90 else "Medium"
                            })
                            break  # Found a suitable target
            
            # Check for GPU optimization
            for node_name, stats in node_analysis.items():
                if stats["hardware"] and stats["hardware"].gpus:
                    ai_vms = [vm for vm in stats["vms"] if any(keyword in vm.get("name", "").lower() for keyword in ["ollama", "ai", "cuda"])]
                    non_ai_vms = [vm for vm in stats["vms"] if vm not in ai_vms and vm.get("status") == "running"]
                    
                    if not ai_vms and non_ai_vms:
                        suggestions.append({
                            "action": f"Consider migrating non-AI VMs from {node_name} to free up GPU node",
                            "benefit": "Reserve GPU-capable node for AI workloads",
                            "priority": "Low"
                        })
            
            # Display suggestions
            if suggestions:
                result.append("**Optimization Suggestions:**")
                
                for i, suggestion in enumerate(suggestions[:5], 1):  # Show top 5
                    priority_emoji = {"High": "🔥", "Medium": "⚡", "Low": "💡"}[suggestion["priority"]]
                    result.append(f"{i}. {priority_emoji} **{suggestion['priority']} Priority**")
                    result.append(f"   Action: {suggestion['action']}")
                    result.append(f"   Benefit: {suggestion['benefit']}")
                    result.append("")
            else:
                result.append("✅ **No optimization suggestions** - Current placement appears optimal!")
            
            return [TextContent(type="text", text="\n".join(result))]
            
        except Exception as e:
            logger.error(f"Failed to analyze placement optimization: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Error analyzing placement optimization: {e}"
            )]
    
    async def generate_diagram(self, format_type: str = "full") -> List[TextContent]:
        """Generate visual infrastructure diagram."""
        try:
            from src.tools.infrastructure_visualizer import InfrastructureVisualizer
            
            # Use current inventory file
            visualizer = InfrastructureVisualizer(str(self.resources_file))
            
            if format_type == "topology":
                diagram = visualizer.generate_topology_diagram()
                title = "🏗️ **Infrastructure Topology Diagram**\n\n```\n"
                content = title + diagram + "\n```"
            elif format_type == "resources":
                diagram = visualizer.generate_resource_utilization()
                content = diagram
            else:  # full
                diagram = visualizer.generate_full_report()
                content = diagram
            
            return [TextContent(type="text", text=content)]
            
        except ImportError:
            return [TextContent(
                type="text",
                text="❌ Infrastructure visualizer not available. Please ensure the module is installed."
            )]
        except Exception as e:
            logger.error(f"Failed to generate diagram: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Error generating diagram: {e}"
            )]
    
    async def list_storage(self) -> List[TextContent]:
        """List all storage pools."""
        try:
            inventory = await self.get_inventory()
            storage = inventory.get("storage", [])
            
            if not storage:
                return [TextContent(
                    type="text",
                    text="No storage pools found."
                )]
            
            # Format storage for display
            result = ["💾 **Storage Pools**\n"]
            for pool in storage:
                name = pool.get("storage", "Unknown")
                pool_type = pool.get("type", "unknown")
                status = pool.get("enabled", False)
                
                status_emoji = "🟢" if status else "🔴"
                
                result.append(f"{status_emoji} **{name}** ({pool_type})")
                
                if "used" in pool and "total" in pool:
                    used_gb = pool["used"] / (1024**3)
                    total_gb = pool["total"] / (1024**3)
                    used_pct = (pool["used"] / pool["total"]) * 100
                    result.append(f"  Usage: {used_gb:.1f}GB / {total_gb:.1f}GB ({used_pct:.1f}%)")
            
            return [TextContent(type="text", text="\n".join(result))]
            
        except Exception as e:
            logger.error(f"Failed to list storage: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Error listing storage: {e}"
            )]
    
    async def list_templates(self) -> List[TextContent]:
        """List all VM templates."""
        try:
            inventory = await self.get_inventory()
            templates = inventory.get("templates", [])
            
            if not templates:
                return [TextContent(
                    type="text",
                    text="No VM templates found. You may need to create template 9000 first."
                )]
            
            # Format templates for display
            result = ["📋 **VM Templates**\n"]
            for template in templates:
                vm_id = template.get("vmid", "?")
                name = template.get("name", "Unknown")
                node = template.get("node", "unknown")
                
                result.append(f"📄 **{name}** (ID: {vm_id}) on {node}")
                
                if "cores" in template:
                    result.append(f"  Config: {template['cores']} cores, {template.get('memory', 0)}MB RAM")
                
                # Highlight the important template 9000
                if vm_id == 9000:
                    result.append("  ⭐ **Primary template for VM creation**")
            
            return [TextContent(type="text", text="\n".join(result))]
            
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Error listing templates: {e}"
            )]
    
    async def discovery_status(self) -> List[TextContent]:
        """Show discovery system status."""
        try:
            # Check if inventory exists and is fresh
            is_stale = await self._is_inventory_stale()
            
            if self.discovery_file.exists():
                with open(self.discovery_file, 'r') as f:
                    discovery_data = json.load(f)
                
                last_update = discovery_data.get("last_update", "Never")
                resource_count = discovery_data.get("resource_count", {})
                
                status_emoji = "🟢" if not is_stale else "🟡"
                
                result = [
                    f"{status_emoji} **Discovery Status**\n",
                    f"Last Update: {last_update}",
                    f"Staleness Threshold: {self.staleness_hours} hours",
                    f"Status: {'Fresh' if not is_stale else 'Stale - refresh recommended'}\n",
                    "**Resource Counts:**"
                ]
                
                for resource_type, count in resource_count.items():
                    result.append(f"  {resource_type.title()}: {count}")
                
            else:
                result = [
                    "🔴 **Discovery Status**\n",
                    "No inventory found. Run discovery to scan Proxmox resources."
                ]
            
            return [TextContent(type="text", text="\n".join(result))]
            
        except Exception as e:
            logger.error(f"Failed to get discovery status: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Error getting discovery status: {e}"
            )]


# Create global instance
discovery_tools = ProxmoxDiscoveryTools()


# MCP Tool definitions for registration
PROXMOX_TOOLS = [
    Tool(
        name="proxmox_list_nodes",
        description="List all Proxmox nodes with status and resource usage",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="proxmox_list_vms", 
        description="List all virtual machines with status and resource usage",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="proxmox_list_storage",
        description="List all storage pools with usage information", 
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="proxmox_list_templates",
        description="List all VM templates available for creating new VMs",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="proxmox_discovery_status",
        description="Show status of the discovery system and inventory freshness",
        inputSchema={
            "type": "object", 
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="proxmox_refresh_inventory",
        description="Force refresh of all Proxmox inventory (nodes, VMs, storage, templates)",
        inputSchema={
            "type": "object",
            "properties": {
                "include_hardware": {
                    "type": "boolean",
                    "description": "Whether to include detailed hardware discovery",
                    "default": True
                }
            },
            "required": []
        }
    ),
    Tool(
        name="proxmox_discover_hardware",
        description="Discover detailed hardware capabilities of Proxmox nodes (GPUs, CPU, storage)",
        inputSchema={
            "type": "object",
            "properties": {
                "node_name": {
                    "type": "string", 
                    "description": "Specific node to discover hardware for (optional, defaults to all nodes)"
                }
            },
            "required": []
        }
    ),
    Tool(
        name="proxmox_suggest_deployment",
        description="Get AI-powered deployment suggestions for workloads based on hardware capabilities",
        inputSchema={
            "type": "object",
            "properties": {
                "workload_type": {
                    "type": "string",
                    "description": "Type of workload to deploy",
                    "enum": ["ai_training", "database", "web_server", "compute", "storage", "general"]
                },
                "requirements": {
                    "type": "object",
                    "properties": {
                        "min_cpu": {"type": "integer", "description": "Minimum CPU cores"},
                        "min_memory_gb": {"type": "integer", "description": "Minimum memory in GB"},
                        "requires_gpu": {"type": "boolean", "description": "Whether GPU is required"},
                        "storage_type": {"type": "string", "enum": ["nvme", "ssd", "hdd", "any"]}
                    }
                }
            },
            "required": ["workload_type"]
        }
    ),
    Tool(
        name="proxmox_optimize_placement",
        description="Analyze current VM placement and suggest optimizations for better resource utilization",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="proxmox_generate_diagram",
        description="Generate visual infrastructure topology diagram and resource utilization charts",
        inputSchema={
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["full", "topology", "resources"],
                    "description": "Type of diagram to generate",
                    "default": "full"
                }
            },
            "required": []
        }
    )
]


# Tool handler functions
async def handle_proxmox_tool(tool_name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle Proxmox discovery tool calls."""
    try:
        if tool_name == "proxmox_list_nodes":
            return await discovery_tools.list_nodes()
        elif tool_name == "proxmox_list_vms":
            # Build comprehensive filters from arguments
            filters = {}
            
            # Legacy status filter support
            if arguments.get("filter"):
                filters["status"] = arguments["filter"]
            
            # New comprehensive filters
            for key in ["status", "name", "id", "os", "node", "min_memory", "min_cpu"]:
                if arguments.get(key):
                    filters[key] = arguments[key]
            
            return await discovery_tools.list_vms(filters=filters if filters else None)
        elif tool_name == "proxmox_list_storage":
            return await discovery_tools.list_storage()
        elif tool_name == "proxmox_list_templates":
            return await discovery_tools.list_templates()
        elif tool_name == "proxmox_discovery_status":
            return await discovery_tools.discovery_status()
        elif tool_name == "proxmox_refresh_inventory":
            include_hardware = arguments.get("include_hardware", True)
            inventory = await discovery_tools.refresh_inventory(include_hardware=include_hardware)
            total = inventory.get("total_resources", 0)
            
            hardware_info = ""
            if include_hardware:
                nodes = inventory.get("nodes", [])
                gpu_count = 0
                for node in nodes:
                    if hasattr(node, 'hardware') and node.hardware:
                        gpu_count += len(node.hardware.gpus)
                    elif isinstance(node, dict) and "hardware" in node:
                        gpu_count += len(node["hardware"].gpus)
                
                hardware_info = f" (including {gpu_count} GPUs detected)"
            
            return [TextContent(
                type="text",
                text=f"✅ Inventory refreshed successfully! Discovered {total} total resources{hardware_info}."
            )]
        elif tool_name == "proxmox_discover_hardware":
            return await discovery_tools.discover_hardware(arguments.get("node_name"))
        elif tool_name == "proxmox_suggest_deployment":
            return await discovery_tools.suggest_deployment(
                arguments.get("workload_type"),
                arguments.get("requirements", {})
            )
        elif tool_name == "proxmox_optimize_placement":
            return await discovery_tools.optimize_placement()
        elif tool_name == "proxmox_generate_diagram":
            return await discovery_tools.generate_diagram(arguments.get("format", "full"))
        else:
            return [TextContent(
                type="text",
                text=f"❌ Unknown tool: {tool_name}"
            )]
    except Exception as e:
        logger.error(f"Error handling tool {tool_name}: {e}")
        return [TextContent(
            type="text",
            text=f"❌ Error executing {tool_name}: {e}"
        )]