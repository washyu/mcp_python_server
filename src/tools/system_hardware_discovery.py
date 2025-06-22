"""
Local System Hardware Discovery Tools
Gathers hardware information from the local system using standard Linux commands.
"""

import asyncio
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)


@dataclass
class SystemCPU:
    """CPU information."""
    model: str = ""
    cores: int = 0
    threads: int = 0
    architecture: str = ""
    frequency_mhz: float = 0.0
    cache_l3_kb: Optional[int] = None
    flags: List[str] = None
    
    def __post_init__(self):
        if self.flags is None:
            self.flags = []


@dataclass
class SystemMemory:
    """Memory information."""
    total_gb: float = 0.0
    available_gb: float = 0.0
    used_gb: float = 0.0
    swap_total_gb: float = 0.0
    swap_used_gb: float = 0.0


@dataclass
class SystemStorage:
    """Storage device information."""
    device: str = ""
    size_gb: float = 0.0
    type: str = ""  # SSD, HDD, NVMe
    model: str = ""
    filesystem: str = ""
    mount_point: str = ""
    used_gb: float = 0.0
    available_gb: float = 0.0


@dataclass
class SystemNetwork:
    """Network interface information."""
    interface: str = ""
    mac_address: str = ""
    ip_addresses: List[str] = None
    speed_mbps: Optional[int] = None
    status: str = ""
    
    def __post_init__(self):
        if self.ip_addresses is None:
            self.ip_addresses = []


@dataclass
class SystemGPU:
    """GPU device information."""
    pci_id: str = ""
    vendor: str = ""
    model: str = ""
    driver: str = ""
    memory_gb: Optional[float] = None


@dataclass
class SystemHardware:
    """Complete system hardware information."""
    hostname: str = ""
    kernel: str = ""
    distribution: str = ""
    uptime_hours: float = 0.0
    cpu: Optional[SystemCPU] = None
    memory: Optional[SystemMemory] = None
    storage: List[SystemStorage] = None
    network: List[SystemNetwork] = None
    gpus: List[SystemGPU] = None
    
    def __post_init__(self):
        if self.storage is None:
            self.storage = []
        if self.network is None:
            self.network = []
        if self.gpus is None:
            self.gpus = []


class SystemHardwareDiscovery:
    """Discovers hardware information from the local system."""
    
    def __init__(self):
        self.discovery_cache = {}
        self.cache_duration = 300  # 5 minutes
    
    async def discover_all_hardware(self) -> SystemHardware:
        """Discover all system hardware information."""
        hardware = SystemHardware()
        
        try:
            # Basic system info
            hardware.hostname = await self._get_hostname()
            hardware.kernel = await self._get_kernel_version()
            hardware.distribution = await self._get_distribution()
            hardware.uptime_hours = await self._get_uptime_hours()
            
            # Hardware components
            hardware.cpu = await self._discover_cpu()
            hardware.memory = await self._discover_memory()
            hardware.storage = await self._discover_storage()
            hardware.network = await self._discover_network()
            hardware.gpus = await self._discover_gpus()
            
        except Exception as e:
            logger.error(f"Failed to discover system hardware: {e}")
        
        return hardware
    
    async def _run_command(self, command: List[str]) -> str:
        """Run a system command and return output."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                return stdout.decode().strip()
            else:
                logger.warning(f"Command {' '.join(command)} failed: {stderr.decode()}")
                return ""
                
        except Exception as e:
            logger.warning(f"Failed to run command {' '.join(command)}: {e}")
            return ""
    
    async def _get_hostname(self) -> str:
        """Get system hostname."""
        return await self._run_command(["hostname"])
    
    async def _get_kernel_version(self) -> str:
        """Get kernel version."""
        return await self._run_command(["uname", "-r"])
    
    async def _get_distribution(self) -> str:
        """Get Linux distribution."""
        # Try /etc/os-release first
        try:
            if Path("/etc/os-release").exists():
                content = Path("/etc/os-release").read_text()
                for line in content.split("\n"):
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip('"')
        except Exception:
            pass
        
        # Fallback to lsb_release
        result = await self._run_command(["lsb_release", "-d"])
        if result:
            return result.split(":", 1)[1].strip()
        
        return "Unknown"
    
    async def _get_uptime_hours(self) -> float:
        """Get system uptime in hours."""
        try:
            uptime_output = await self._run_command(["cat", "/proc/uptime"])
            if uptime_output:
                uptime_seconds = float(uptime_output.split()[0])
                return uptime_seconds / 3600
        except Exception:
            pass
        return 0.0
    
    async def _discover_cpu(self) -> SystemCPU:
        """Discover CPU information."""
        cpu = SystemCPU()
        
        try:
            # Use lscpu for detailed CPU info
            lscpu_output = await self._run_command(["lscpu"])
            if lscpu_output:
                for line in lscpu_output.split("\n"):
                    if "Model name:" in line:
                        cpu.model = line.split(":", 1)[1].strip()
                    elif "CPU(s):" in line and "On-line" not in line:
                        cpu.threads = int(line.split(":", 1)[1].strip())
                    elif "Core(s) per socket:" in line:
                        cores_per_socket = int(line.split(":", 1)[1].strip())
                        sockets = 1  # Default
                        cpu.cores = cores_per_socket * sockets
                    elif "Socket(s):" in line:
                        sockets = int(line.split(":", 1)[1].strip())
                        if hasattr(cpu, 'cores') and cpu.cores > 0:
                            cpu.cores = (cpu.cores // 1) * sockets  # Recalculate
                    elif "Architecture:" in line:
                        cpu.architecture = line.split(":", 1)[1].strip()
                    elif "CPU max MHz:" in line:
                        cpu.frequency_mhz = float(line.split(":", 1)[1].strip())
                    elif "L3 cache:" in line:
                        cache_str = line.split(":", 1)[1].strip()
                        if "K" in cache_str:
                            cpu.cache_l3_kb = int(cache_str.replace("K", "").strip())
                        elif "M" in cache_str:
                            cpu.cache_l3_kb = int(float(cache_str.replace("M", "").strip()) * 1024)
            
            # Get CPU flags
            cpuinfo_output = await self._run_command(["cat", "/proc/cpuinfo"])
            if cpuinfo_output:
                for line in cpuinfo_output.split("\n"):
                    if line.startswith("flags") or line.startswith("Features"):
                        flags_str = line.split(":", 1)[1].strip()
                        cpu.flags = flags_str.split()
                        break
        
        except Exception as e:
            logger.warning(f"Failed to discover CPU: {e}")
        
        return cpu
    
    async def _discover_memory(self) -> SystemMemory:
        """Discover memory information."""
        memory = SystemMemory()
        
        try:
            meminfo_output = await self._run_command(["cat", "/proc/meminfo"])
            if meminfo_output:
                mem_values = {}
                for line in meminfo_output.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        # Convert kB to GB
                        kb_value = int(value.strip().split()[0])
                        mem_values[key.strip()] = kb_value / (1024 * 1024)
                
                memory.total_gb = mem_values.get("MemTotal", 0)
                memory.available_gb = mem_values.get("MemAvailable", 0)
                memory.used_gb = memory.total_gb - memory.available_gb
                memory.swap_total_gb = mem_values.get("SwapTotal", 0)
                memory.swap_used_gb = memory.swap_total_gb - mem_values.get("SwapFree", 0)
        
        except Exception as e:
            logger.warning(f"Failed to discover memory: {e}")
        
        return memory
    
    async def _discover_storage(self) -> List[SystemStorage]:
        """Discover storage devices."""
        storage_devices = []
        
        try:
            # Use lsblk for block device information
            lsblk_output = await self._run_command(["lsblk", "-J", "-o", "NAME,SIZE,TYPE,MODEL,FSTYPE,MOUNTPOINT"])
            if lsblk_output:
                lsblk_data = json.loads(lsblk_output)
                
                for device in lsblk_data.get("blockdevices", []):
                    if device.get("type") == "disk":
                        storage = SystemStorage()
                        storage.device = f"/dev/{device.get('name', '')}"
                        storage.model = device.get("model", "Unknown")
                        storage.type = await self._classify_storage_type(storage.device)
                        
                        # Parse size
                        size_str = device.get("size", "0")
                        storage.size_gb = self._parse_size_to_gb(size_str)
                        
                        # Check for mounted partitions
                        children = device.get("children", [])
                        for child in children:
                            if child.get("mountpoint"):
                                storage.filesystem = child.get("fstype", "")
                                storage.mount_point = child.get("mountpoint", "")
                                
                                # Get usage for mounted filesystems
                                if storage.mount_point:
                                    usage = await self._get_filesystem_usage(storage.mount_point)
                                    storage.used_gb = usage.get("used_gb", 0)
                                    storage.available_gb = usage.get("available_gb", 0)
                                break
                        
                        storage_devices.append(storage)
        
        except Exception as e:
            logger.warning(f"Failed to discover storage: {e}")
        
        return storage_devices
    
    async def _classify_storage_type(self, device: str) -> str:
        """Classify storage device type (SSD, HDD, NVMe)."""
        try:
            if "nvme" in device:
                return "NVMe"
            
            # Check rotation (0 = SSD, 1 = HDD)
            device_name = device.replace("/dev/", "")
            rotational_file = f"/sys/block/{device_name}/queue/rotational"
            
            if Path(rotational_file).exists():
                rotational = Path(rotational_file).read_text().strip()
                return "SSD" if rotational == "0" else "HDD"
        
        except Exception:
            pass
        
        return "Unknown"
    
    def _parse_size_to_gb(self, size_str: str) -> float:
        """Parse size string to GB."""
        try:
            size_str = size_str.upper().strip()
            if "G" in size_str:
                return float(size_str.replace("G", ""))
            elif "T" in size_str:
                return float(size_str.replace("T", "")) * 1024
            elif "M" in size_str:
                return float(size_str.replace("M", "")) / 1024
            elif "K" in size_str:
                return float(size_str.replace("K", "")) / (1024 * 1024)
            else:
                # Assume bytes
                return float(size_str) / (1024**3)
        except Exception:
            return 0.0
    
    async def _get_filesystem_usage(self, mount_point: str) -> Dict[str, float]:
        """Get filesystem usage for a mount point."""
        try:
            df_output = await self._run_command(["df", "-BG", mount_point])
            if df_output:
                lines = df_output.strip().split("\n")
                if len(lines) >= 2:
                    fields = lines[1].split()
                    if len(fields) >= 4:
                        return {
                            "used_gb": float(fields[2].replace("G", "")),
                            "available_gb": float(fields[3].replace("G", ""))
                        }
        except Exception:
            pass
        
        return {"used_gb": 0.0, "available_gb": 0.0}
    
    async def _discover_network(self) -> List[SystemNetwork]:
        """Discover network interfaces."""
        interfaces = []
        
        try:
            # Use ip command for network interface info
            ip_output = await self._run_command(["ip", "-j", "addr"])
            if ip_output:
                ip_data = json.loads(ip_output)
                
                for interface_data in ip_data:
                    if interface_data.get("ifname") != "lo":  # Skip loopback
                        interface = SystemNetwork()
                        interface.interface = interface_data.get("ifname", "")
                        interface.mac_address = interface_data.get("address", "")
                        interface.status = "up" if "UP" in interface_data.get("flags", []) else "down"
                        
                        # Get IP addresses
                        addr_info = interface_data.get("addr_info", [])
                        for addr in addr_info:
                            if addr.get("family") in ["inet", "inet6"]:
                                interface.ip_addresses.append(addr.get("local", ""))
                        
                        # Try to get speed information
                        speed_file = f"/sys/class/net/{interface.interface}/speed"
                        if Path(speed_file).exists():
                            try:
                                speed_content = Path(speed_file).read_text().strip()
                                interface.speed_mbps = int(speed_content)
                            except Exception:
                                pass
                        
                        interfaces.append(interface)
        
        except Exception as e:
            logger.warning(f"Failed to discover network interfaces: {e}")
        
        return interfaces
    
    async def _discover_gpus(self) -> List[SystemGPU]:
        """Discover GPU devices."""
        gpus = []
        
        try:
            # Use lspci to find GPU devices
            lspci_output = await self._run_command(["lspci", "-v"])
            if lspci_output:
                current_gpu = None
                
                for line in lspci_output.split("\n"):
                    # Look for VGA or 3D controller lines
                    if "VGA" in line or "3D controller" in line:
                        if current_gpu:
                            gpus.append(current_gpu)
                        
                        current_gpu = SystemGPU()
                        # Parse PCI ID and device info
                        parts = line.split()
                        if parts:
                            current_gpu.pci_id = parts[0]
                        
                        # Extract vendor and model
                        if ":" in line:
                            device_info = line.split(":", 1)[1].strip()
                            if "[" in device_info and "]" in device_info:
                                # Format: Vendor [vendor_id:device_id]
                                vendor_part = device_info.split("[")[0].strip()
                                current_gpu.vendor = vendor_part
                                current_gpu.model = device_info
                            else:
                                current_gpu.model = device_info
                    
                    elif current_gpu and line.startswith("\tKernel driver in use:"):
                        current_gpu.driver = line.split(":", 1)[1].strip()
                
                if current_gpu:
                    gpus.append(current_gpu)
            
            # Try to get NVIDIA GPU memory if nvidia-smi is available
            try:
                nvidia_output = await self._run_command(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"])
                if nvidia_output:
                    memory_values = nvidia_output.strip().split("\n")
                    for i, gpu in enumerate(gpus):
                        if "nvidia" in gpu.vendor.lower() and i < len(memory_values):
                            try:
                                gpu.memory_gb = float(memory_values[i]) / 1024
                            except Exception:
                                pass
            except Exception:
                pass  # nvidia-smi not available
        
        except Exception as e:
            logger.warning(f"Failed to discover GPUs: {e}")
        
        return gpus


# Initialize platform-specific discovery manager
import platform
if platform.system() == "Darwin":
    from .macos_hardware_discovery import MacOSHardwareDiscovery
    hardware_discovery = MacOSHardwareDiscovery()
else:
    hardware_discovery = SystemHardwareDiscovery()


async def discover_local_hardware_impl() -> List[TextContent]:
    """Implementation of discover_local_hardware tool."""
    hardware = await hardware_discovery.discover_all_hardware()
    
    result = ["🖥️ **Local System Hardware Discovery**\n"]
    
    # System Information
    result.append(f"**System**: {hardware.hostname}")
    result.append(f"**Distribution**: {hardware.distribution}")
    result.append(f"**Kernel**: {hardware.kernel}")
    result.append(f"**Uptime**: {hardware.uptime_hours:.1f} hours\n")
    
    # CPU Information
    if hardware.cpu:
        cpu = hardware.cpu
        result.append("**🔧 CPU Information**")
        result.append(f"  Model: {cpu.model}")
        result.append(f"  Architecture: {cpu.architecture}")
        result.append(f"  Cores: {cpu.cores}, Threads: {cpu.threads}")
        result.append(f"  Max Frequency: {cpu.frequency_mhz:.0f} MHz")
        if cpu.cache_l3_kb:
            result.append(f"  L3 Cache: {cpu.cache_l3_kb} KB")
        result.append("")
    
    # Memory Information
    if hardware.memory:
        mem = hardware.memory
        result.append("**💾 Memory Information**")
        result.append(f"  Total: {mem.total_gb:.1f} GB")
        result.append(f"  Used: {mem.used_gb:.1f} GB ({mem.used_gb/mem.total_gb*100:.1f}%)")
        result.append(f"  Available: {mem.available_gb:.1f} GB")
        if mem.swap_total_gb > 0:
            result.append(f"  Swap: {mem.swap_used_gb:.1f}/{mem.swap_total_gb:.1f} GB")
        result.append("")
    
    # Storage Information
    if hardware.storage:
        result.append("**💽 Storage Devices**")
        for storage in hardware.storage:
            result.append(f"  **{storage.device}** ({storage.type})")
            result.append(f"    Model: {storage.model}")
            result.append(f"    Size: {storage.size_gb:.1f} GB")
            if storage.mount_point:
                result.append(f"    Mounted: {storage.mount_point} ({storage.filesystem})")
                result.append(f"    Used: {storage.used_gb:.1f}/{storage.size_gb:.1f} GB")
        result.append("")
    
    # Network Information
    if hardware.network:
        result.append("**🌐 Network Interfaces**")
        for net in hardware.network:
            result.append(f"  **{net.interface}** ({net.status})")
            if net.ip_addresses:
                result.append(f"    IP: {', '.join(net.ip_addresses)}")
            result.append(f"    MAC: {net.mac_address}")
            if net.speed_mbps:
                result.append(f"    Speed: {net.speed_mbps} Mbps")
        result.append("")
    
    # GPU Information
    if hardware.gpus:
        result.append("**🎮 GPU Devices**")
        for gpu in hardware.gpus:
            result.append(f"  **{gpu.pci_id}** {gpu.model}")
            if gpu.driver:
                result.append(f"    Driver: {gpu.driver}")
            if gpu.memory_gb:
                result.append(f"    Memory: {gpu.memory_gb:.1f} GB")
        result.append("")
    
    return [TextContent(type="text", text="\n".join(result))]


async def get_system_resource_summary_impl() -> List[TextContent]:
    """Implementation of get_system_resource_summary tool."""
    hardware = await hardware_discovery.discover_all_hardware()
    
    summary = ["📊 **System Resource Summary**\n"]
    
    # Quick overview
    if hardware.cpu and hardware.memory:
        summary.append(f"**{hardware.hostname}** ({hardware.distribution})")
        summary.append(f"CPU: {hardware.cpu.cores} cores, {hardware.cpu.threads} threads")
        summary.append(f"Memory: {hardware.memory.used_gb:.1f}/{hardware.memory.total_gb:.1f} GB ({hardware.memory.used_gb/hardware.memory.total_gb*100:.1f}% used)")
        
        total_storage = sum(s.size_gb for s in hardware.storage)
        if total_storage > 0:
            summary.append(f"Storage: {total_storage:.1f} GB total across {len(hardware.storage)} devices")
        
        if hardware.gpus:
            summary.append(f"GPUs: {len(hardware.gpus)} device(s)")
    
    return [TextContent(type="text", text="\n".join(summary))]


def register_system_hardware_tools(server):
    """Register system hardware discovery tools with the MCP server."""
    
    @server.tool()
    async def discover_local_hardware() -> List[TextContent]:
        """Discover all hardware information from the local system."""
        return await discover_local_hardware_impl()
    
    @server.tool()
    async def get_system_resource_summary() -> List[TextContent]:
        """Get a quick summary of system resources (CPU, memory, storage)."""
        return await get_system_resource_summary_impl()


# Tool definitions for registration
SYSTEM_HARDWARE_TOOLS = [
    Tool(
        name="discover_local_hardware",
        description="Get detailed hardware specs (CPU, memory, storage, GPU) from the LOCAL MCP server system - NOT for remote systems",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="get_system_resource_summary", 
        description="Get a quick summary of system resources (CPU, memory, storage)",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )
]


async def handle_system_hardware_tool(tool_name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle system hardware discovery tool calls."""
    
    if tool_name == "discover_local_hardware":
        return await discover_local_hardware_impl()
    elif tool_name == "get_system_resource_summary":
        return await get_system_resource_summary_impl()
    else:
        return [TextContent(
            type="text",
            text=f"❌ Unknown system hardware tool: {tool_name}"
        )]