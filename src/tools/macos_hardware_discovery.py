"""
macOS System Hardware Discovery Tools
Gathers hardware information from macOS systems using system_profiler and other native commands.
"""

import asyncio
import json
import logging
import plistlib
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

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


class MacOSHardwareDiscovery:
    """Hardware discovery for macOS systems."""
    
    def __init__(self):
        self.discovery_cache = {}
        self.cache_duration = 300  # 5 minutes
    
    async def discover_all_hardware(self) -> SystemHardware:
        """Discover all system hardware information on macOS."""
        hardware = SystemHardware()
        
        try:
            # Basic system info
            hardware.hostname = await self._get_hostname()
            hardware.kernel = await self._get_kernel_version()
            hardware.distribution = await self._get_macos_version()
            hardware.uptime_hours = await self._get_uptime_hours()
            
            # Get system profiler data
            system_data = await self._get_system_profiler_data()
            
            # Hardware components
            hardware.cpu = await self._discover_cpu_macos(system_data)
            hardware.memory = await self._discover_memory_macos(system_data)
            hardware.storage = await self._discover_storage_macos(system_data)
            hardware.network = await self._discover_network_macos(system_data)
            hardware.gpus = await self._discover_gpus_macos(system_data)
            
        except Exception as e:
            logger.error(f"Failed to discover system hardware on macOS: {e}")
        
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
    
    async def _get_macos_version(self) -> str:
        """Get macOS version."""
        try:
            version_output = await self._run_command(["sw_vers", "-productVersion"])
            name_output = await self._run_command(["sw_vers", "-productName"])
            if version_output and name_output:
                return f"{name_output} {version_output}"
            elif version_output:
                return f"macOS {version_output}"
        except Exception:
            pass
        return "macOS (Unknown Version)"
    
    async def _get_uptime_hours(self) -> float:
        """Get system uptime in hours."""
        try:
            uptime_output = await self._run_command(["uptime"])
            if uptime_output:
                # Parse uptime output: "up X days, Y hours" or "up X:Y"
                if "day" in uptime_output:
                    # Format: "up 2 days, 3:45"
                    import re
                    day_match = re.search(r"up (\d+) day", uptime_output)
                    time_match = re.search(r"(\d+):(\d+)", uptime_output)
                    
                    days = int(day_match.group(1)) if day_match else 0
                    hours = int(time_match.group(1)) if time_match else 0
                    minutes = int(time_match.group(2)) if time_match else 0
                    
                    return days * 24 + hours + minutes / 60
                elif ":" in uptime_output:
                    # Format: "up 3:45"
                    import re
                    time_match = re.search(r"up (\d+):(\d+)", uptime_output)
                    if time_match:
                        hours = int(time_match.group(1))
                        minutes = int(time_match.group(2))
                        return hours + minutes / 60
        except Exception:
            pass
        return 0.0
    
    async def _get_system_profiler_data(self) -> Dict[str, Any]:
        """Get system profiler data in JSON format."""
        try:
            # Get hardware overview
            hardware_output = await self._run_command([
                "system_profiler", "-json", 
                "SPHardwareDataType",
                "SPMemoryDataType", 
                "SPStorageDataType",
                "SPNetworkDataType",
                "SPDisplaysDataType"
            ])
            
            if hardware_output:
                return json.loads(hardware_output)
        except Exception as e:
            logger.warning(f"Failed to get system profiler data: {e}")
        
        return {}
    
    async def _discover_cpu_macos(self, system_data: Dict[str, Any]) -> SystemCPU:
        """Discover CPU information on macOS."""
        cpu = SystemCPU()
        
        try:
            hardware_data = system_data.get("SPHardwareDataType", [])
            if hardware_data:
                hw = hardware_data[0]
                
                cpu.model = hw.get("chip_type", hw.get("cpu_type", "Unknown"))
                cpu.cores = int(hw.get("number_processors", 0))
                cpu.threads = cpu.cores  # macOS doesn't typically report threads separately
                
                # Get frequency
                freq_str = hw.get("current_processor_speed", "")
                if freq_str:
                    # Parse frequency like "3.2 GHz"
                    freq_match = re.search(r"([\d.]+)\s*(GHz|MHz)", freq_str)
                    if freq_match:
                        freq_value = float(freq_match.group(1))
                        unit = freq_match.group(2)
                        cpu.frequency_mhz = freq_value * 1000 if unit == "GHz" else freq_value
                
                # Architecture (Apple Silicon vs Intel)
                if "Apple" in cpu.model:
                    cpu.architecture = "Apple Silicon"
                else:
                    cpu.architecture = "x86_64"
        
        except Exception as e:
            logger.warning(f"Failed to discover CPU on macOS: {e}")
        
        return cpu
    
    async def _discover_memory_macos(self, system_data: Dict[str, Any]) -> SystemMemory:
        """Discover memory information on macOS."""
        memory = SystemMemory()
        
        try:
            # Get total memory from hardware data
            hardware_data = system_data.get("SPHardwareDataType", [])
            if hardware_data:
                hw = hardware_data[0]
                mem_str = hw.get("physical_memory", "")
                if mem_str:
                    # Parse memory like "16 GB"
                    mem_match = re.search(r"(\d+)\s*GB", mem_str)
                    if mem_match:
                        memory.total_gb = float(mem_match.group(1))
            
            # Get memory usage using vm_stat
            vm_stat_output = await self._run_command(["vm_stat"])
            if vm_stat_output:
                # Parse vm_stat output to get memory usage
                page_size = 4096  # Default page size
                
                for line in vm_stat_output.split("\n"):
                    if "page size of" in line:
                        page_match = re.search(r"page size of (\d+) bytes", line)
                        if page_match:
                            page_size = int(page_match.group(1))
                    elif "Pages free:" in line:
                        free_match = re.search(r"Pages free:\s+(\d+)", line)
                        if free_match:
                            free_pages = int(free_match.group(1).replace(".", ""))
                            free_gb = (free_pages * page_size) / (1024**3)
                            memory.available_gb = free_gb
                            memory.used_gb = memory.total_gb - free_gb
        
        except Exception as e:
            logger.warning(f"Failed to discover memory on macOS: {e}")
        
        return memory
    
    async def _discover_storage_macos(self, system_data: Dict[str, Any]) -> List[SystemStorage]:
        """Discover storage devices on macOS."""
        storage_devices = []
        
        try:
            # Get disk usage using df
            df_output = await self._run_command(["df", "-h"])
            if df_output:
                lines = df_output.strip().split("\n")[1:]  # Skip header
                
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 6 and parts[0].startswith("/dev/"):
                        storage = SystemStorage()
                        storage.device = parts[0]
                        storage.filesystem = "APFS"  # Most likely on modern macOS
                        storage.mount_point = parts[5] if len(parts) >= 6 else ""
                        
                        # Parse sizes (remove 'i' from Gi, Ti, etc.)
                        size_str = parts[1].replace("i", "")
                        used_str = parts[2].replace("i", "")
                        avail_str = parts[3].replace("i", "")
                        
                        storage.size_gb = self._parse_size_to_gb(size_str)
                        storage.used_gb = self._parse_size_to_gb(used_str)
                        storage.available_gb = self._parse_size_to_gb(avail_str)
                        
                        # Try to determine storage type (SSD is most common on Mac)
                        storage.type = "SSD"  # Default assumption for macOS
                        
                        # Get model info if available
                        storage.model = "Apple Internal Storage"  # Default
                        
                        storage_devices.append(storage)
            
            # Try to get more detailed storage info from system_profiler
            storage_data = system_data.get("SPStorageDataType", [])
            for storage_info in storage_data:
                # Update storage devices with more detailed info
                for storage in storage_devices:
                    if storage.mount_point == "/":  # Main drive
                        storage.model = storage_info.get("device_name", storage.model)
                        media_type = storage_info.get("medium_type", "")
                        if "SSD" in media_type:
                            storage.type = "SSD"
                        elif "Flash" in media_type:
                            storage.type = "Flash"
                        break
        
        except Exception as e:
            logger.warning(f"Failed to discover storage on macOS: {e}")
        
        return storage_devices
    
    def _parse_size_to_gb(self, size_str: str) -> float:
        """Parse size string to GB (macOS format)."""
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
                # Assume GB
                return float(size_str)
        except Exception:
            return 0.0
    
    async def _discover_network_macos(self, system_data: Dict[str, Any]) -> List[SystemNetwork]:
        """Discover network interfaces on macOS."""
        interfaces = []
        
        try:
            # Use ifconfig to get network interface info
            ifconfig_output = await self._run_command(["ifconfig"])
            if ifconfig_output:
                current_interface = None
                
                for line in ifconfig_output.split("\n"):
                    # New interface line
                    if line and not line.startswith("\t") and not line.startswith(" "):
                        if current_interface:
                            interfaces.append(current_interface)
                        
                        # Parse interface name
                        interface_name = line.split(":")[0].strip()
                        if interface_name != "lo0":  # Skip loopback
                            current_interface = SystemNetwork()
                            current_interface.interface = interface_name
                            
                            # Check if interface is up
                            current_interface.status = "up" if "UP" in line else "down"
                    
                    elif current_interface and line.strip():
                        # Parse interface details
                        if "ether" in line:
                            # MAC address
                            parts = line.strip().split()
                            if len(parts) >= 2:
                                current_interface.mac_address = parts[1]
                        elif "inet " in line:
                            # IP address
                            parts = line.strip().split()
                            if len(parts) >= 2:
                                current_interface.ip_addresses.append(parts[1])
                
                # Add the last interface
                if current_interface:
                    interfaces.append(current_interface)
        
        except Exception as e:
            logger.warning(f"Failed to discover network interfaces on macOS: {e}")
        
        return interfaces
    
    async def _discover_gpus_macos(self, system_data: Dict[str, Any]) -> List[SystemGPU]:
        """Discover GPU devices on macOS."""
        gpus = []
        
        try:
            displays_data = system_data.get("SPDisplaysDataType", [])
            
            for display_info in displays_data:
                gpu = SystemGPU()
                
                # Get GPU info
                gpu.model = display_info.get("sppci_model", "Unknown GPU")
                gpu.vendor = "Apple" if "Apple" in gpu.model else "Unknown"
                
                # Get memory info
                vram_str = display_info.get("sppci_vram", "")
                if vram_str:
                    # Parse VRAM like "8 GB"
                    vram_match = re.search(r"(\d+)\s*GB", vram_str)
                    if vram_match:
                        gpu.memory_gb = float(vram_match.group(1))
                
                # Get PCI info if available
                pci_id = display_info.get("sppci_device_id", "")
                if pci_id:
                    gpu.pci_id = pci_id
                
                gpus.append(gpu)
        
        except Exception as e:
            logger.warning(f"Failed to discover GPUs on macOS: {e}")
        
        return gpus


# Create platform-specific discovery instance
import platform
if platform.system() == "Darwin":
    hardware_discovery_platform = MacOSHardwareDiscovery()
else:
    # Use the Linux version for other platforms
    from .system_hardware_discovery import SystemHardwareDiscovery
    hardware_discovery_platform = SystemHardwareDiscovery()