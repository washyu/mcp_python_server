#!/usr/bin/env python3
"""
Homelab AI Chat Interface
Provides an interactive chat interface for AI-driven homelab automation.
"""

import asyncio
import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

# Rich for beautiful console output
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.text import Text
    from rich.live import Live
    from rich.table import Table
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: Rich not available, using basic console output")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.tools.ollama_assistant import get_ollama_assistant
from src.server.websocket_server import main as start_websocket_server
from src.tools.homelab_tools import HOMELAB_TOOLS, handle_homelab_tool
from src.tools.agent_homelab_tools import AGENT_HOMELAB_TOOLS, handle_agent_homelab_tool
from src.tools.lxd_tools import LXD_TOOLS, handle_lxd_tool
from src.tools.proxmox_discovery import PROXMOX_TOOLS, handle_proxmox_tool


# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise during normal operation
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set to INFO for normal operation (can be enabled via debug command)
logger.setLevel(logging.INFO)


@dataclass
class ChatConfig:
    """Configuration for the chat interface."""
    ollama_host: str = "localhost"
    ollama_port: int = 11434
    ollama_model: str = "deepseek-r1:8b"
    websocket_port: int = 8765
    auto_start_server: bool = True


class HomelabChatInterface:
    """Interactive chat interface for homelab automation."""
    
    def __init__(self, config: ChatConfig):
        self.config = config
        self.console = Console() if RICH_AVAILABLE else None
        self.ollama_assistant = get_ollama_assistant()
        self.conversation_history: List[Dict[str, str]] = []
        self.server_task: Optional[asyncio.Task] = None
        self.verbose_logging = False
        # Combine all available MCP tools
        self.mcp_tools = AGENT_HOMELAB_TOOLS + LXD_TOOLS + HOMELAB_TOOLS + PROXMOX_TOOLS
        self.tool_execution_enabled = True
        self.current_server = None  # Track the current working server
        self._detected_hostname = None
        
    def print(self, message: str, style: Optional[str] = None):
        """Print message with optional styling."""
        if self.console:
            if style:
                self.console.print(message, style=style)
            else:
                self.console.print(message)
        else:
            print(message)
            
    def print_panel(self, message: str, title: str = "", style: str = "blue"):
        """Print a styled panel."""
        if self.console:
            self.console.print(Panel(message, title=title, border_style=style))
        else:
            print(f"\n=== {title} ===")
            print(message)
            print("=" * (len(title) + 8))
            
    def print_markdown(self, content: str):
        """Print markdown content."""
        if self.console:
            self.console.print(Markdown(content))
        else:
            print(content)
            
    async def check_dependencies(self) -> Dict[str, bool]:
        """Check if all required services are available."""
        status = {}
        
        # Check Ollama
        self.print("🔍 Checking Ollama service...", "yellow")
        ollama_status = await self.ollama_assistant.check_ollama_status(
            self.config.ollama_host, 
            self.config.ollama_port
        )
        status['ollama'] = ollama_status['status'] == 'running'
        
        if status['ollama']:
            models = ollama_status.get('available_models', [])
            if self.config.ollama_model in models:
                status['model'] = True
                self.print(f"✅ Ollama running with {self.config.ollama_model}", "green")
            else:
                status['model'] = False
                self.print(f"⚠️  Model {self.config.ollama_model} not found", "yellow")
                self.print(f"Available models: {', '.join(models)}", "dim")
        else:
            status['model'] = False
            self.print("❌ Ollama not running", "red")
            
        return status
        
    async def setup_ollama_if_needed(self) -> bool:
        """Set up Ollama if it's not running or missing model."""
        status = await self.check_dependencies()
        
        if not status['ollama']:
            self.print_panel(
                "Ollama AI service is not running.\n\n"
                "Ollama provides free, private AI assistance for your homelab.\n"
                "Would you like help setting it up?",
                "🤖 Ollama Setup Required",
                "yellow"
            )
            
            if self.console:
                setup = Confirm.ask("Set up Ollama now?")
            else:
                setup = input("Set up Ollama now? (y/n): ").lower().startswith('y')
                
            if setup:
                self.print("📋 Generating Ollama setup guide...", "blue")
                
                # Generate setup guide
                guide = await self.ollama_assistant.generate_setup_guide(
                    hardware_type="generic",
                    available_memory=8,  # Assume reasonable default
                    gpu_available=False
                )
                
                self.print_panel(
                    f"Hardware: {guide.hardware_type}\n\n" +
                    "\n".join([
                        f"{step['step']}. {step['action']}\n"
                        f"   Command: {step['command']}\n"
                        f"   Note: {step['note']}\n"
                        for step in guide.steps
                    ]),
                    "🔧 Ollama Setup Guide",
                    "blue"
                )
                
                return False  # User needs to set up manually
            else:
                self.print("Continuing without local AI...", "yellow")
                return False
                
        elif not status['model']:
            self.print(f"Model {self.config.ollama_model} not available.", "yellow")
            
            # Suggest model
            suggestion = await self.ollama_assistant.suggest_model(
                use_case="homelab assistance",
                available_memory=8
            )
            
            self.print_panel(
                f"Recommended model: {suggestion['recommended']['name']}\n"
                f"Reason: {suggestion['recommended']['reason']}\n"
                f"Size: {suggestion['recommended']['size']}\n\n"
                f"Install command: {suggestion['recommended']['pull_command']}",
                "🎯 Model Recommendation",
                "blue"
            )
            
            return False
            
        return True
        
    async def start_mcp_server(self):
        """Start the MCP WebSocket server in background."""
        if self.config.auto_start_server:
            self.print(f"🚀 Starting MCP server on port {self.config.websocket_port}...", "blue")
            
            # Start server in background
            self.server_task = asyncio.create_task(start_websocket_server())
            
            # Give it a moment to start
            await asyncio.sleep(2)
            self.print("✅ MCP server started", "green")
            
    async def discover_hardware_resources(self, host: str = None) -> Dict[str, Any]:
        """Discover actual hardware resources from target systems."""
        hardware_info = {
            "discovery_timestamp": datetime.now().isoformat(),
            "systems": {}
        }
        
        # Import necessary modules for hardware discovery
        try:
            import paramiko
            import json
            import subprocess
            import platform
        except ImportError as e:
            logger.warning(f"Hardware discovery limited due to missing dependencies: {e}")
            return hardware_info
        
        # Discover local system first
        try:
            local_info = {
                "hostname": platform.node(),
                "architecture": platform.machine(),
                "platform": platform.system(),
                "cpu_count": None,
                "memory_gb": None,
                "disk_space_gb": None
            }
            
            # Get CPU count
            try:
                if platform.system() == "Darwin":  # macOS
                    local_info["cpu_count"] = int(subprocess.check_output(
                        ["sysctl", "-n", "hw.ncpu"], text=True
                    ).strip())
                else:  # Linux
                    local_info["cpu_count"] = int(subprocess.check_output(
                        ["nproc"], text=True
                    ).strip())
            except:
                pass
                
            # Get memory info
            try:
                if platform.system() == "Linux":
                    with open("/proc/meminfo", "r") as f:
                        for line in f:
                            if line.startswith("MemTotal:"):
                                kb = int(line.split()[1])
                                local_info["memory_gb"] = round(kb / 1024 / 1024, 1)
                                break
                elif platform.system() == "Darwin":  # macOS
                    result = subprocess.check_output(
                        ["sysctl", "-n", "hw.memsize"], text=True
                    ).strip()
                    local_info["memory_gb"] = round(int(result) / 1024 / 1024 / 1024, 1)
            except:
                pass
                
            # Get disk space
            try:
                result = subprocess.check_output(
                    ["df", "-h", "/"], text=True
                ).split('\n')[1].split()
                local_info["disk_space_gb"] = result[1]  # Available space
            except:
                pass
                
            hardware_info["systems"]["local"] = local_info
            
        except Exception as e:
            logger.error(f"Failed to discover local hardware: {e}")
        
        # Discover Raspberry Pi if host provided
        if host:
            try:
                # Try to connect and get hardware info
                pi_info = await self._discover_remote_hardware(host)
                if pi_info:
                    hardware_info["systems"][host] = pi_info
            except Exception as e:
                logger.error(f"Failed to discover remote hardware for {host}: {e}")
                
        return hardware_info
        
    async def _discover_remote_hardware(self, host: str) -> Dict[str, Any]:
        """Discover hardware on a remote system via SSH."""
        try:
            import paramiko
            import asyncio
            import concurrent.futures
            
            def ssh_discovery():
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                # Try common credentials (in production, use proper key management)
                credentials = [
                    ("pi", "raspberry"),
                    ("ubuntu", "ubuntu"),
                    ("pi", "pi"),
                ]
                
                connected = False
                for username, password in credentials:
                    try:
                        ssh.connect(host, username=username, password=password, timeout=10)
                        connected = True
                        break
                    except:
                        continue
                        
                if not connected:
                    return None
                    
                commands = {
                    "hostname": "hostname",
                    "architecture": "uname -m",
                    "platform": "uname -s",
                    "cpu_count": "nproc",
                    "memory_kb": "grep MemTotal /proc/meminfo | awk '{print $2}'",
                    "cpu_model": "grep 'model name' /proc/cpuinfo | head -1 | cut -d: -f2 | xargs",
                    "disk_space": "df -h / | tail -1 | awk '{print $2, $3, $4}'",
                    "os_release": "cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"'",
                    # Storage discovery
                    "storage_devices": "lsblk -d -o NAME,SIZE,TYPE,MODEL | grep -E '(disk|nvme)' || echo 'No storage info'",
                    "mount_points": "df -h | grep -E '^/' | awk '{print $1, $2, $6}' || echo 'No mount info'",
                    "storage_types": "lsblk -o NAME,TYPE,FSTYPE,SIZE | grep -v loop || echo 'No block devices'",
                    # GPU discovery
                    "gpu_nvidia": "nvidia-smi -L 2>/dev/null || echo 'No NVIDIA GPU'",
                    "gpu_amd": "lspci | grep -i 'vga\\|3d\\|display' | grep -i amd || echo 'No AMD GPU'",
                    "gpu_intel": "lspci | grep -i 'vga\\|3d\\|display' | grep -i intel || echo 'No Intel GPU'",
                    "gpu_general": "lspci | grep -i 'vga\\|3d\\|display' || echo 'No GPU found'",
                    # Network discovery
                    "network_interfaces": "ip link show | grep -E '^[0-9]+:' | awk '{print $2}' | tr -d ':' || echo 'No network info'",
                    "network_speeds": "for iface in $(ip link show | grep -E '^[0-9]+:' | awk '{print $2}' | tr -d ':' | grep -v lo); do echo \"$iface: $(ethtool $iface 2>/dev/null | grep Speed | awk '{print $2}' || echo 'Unknown')\"; done || echo 'No speed info'",
                    # USB and expansion
                    "usb_devices": "lsusb | wc -l && lsusb | head -5 || echo 'No USB info'",
                    "pci_devices": "lspci | grep -E 'Network|Ethernet|WiFi|Audio|GPU|Graphics' || echo 'No PCI expansion'"
                }
                
                results = {}
                for key, cmd in commands.items():
                    try:
                        stdin, stdout, stderr = ssh.exec_command(cmd)
                        output = stdout.read().decode().strip()
                        results[key] = output
                    except:
                        results[key] = None
                        
                ssh.close()
                
                # Process results
                hardware_info = {
                    "hostname": results.get("hostname"),
                    "architecture": results.get("architecture"),
                    "platform": results.get("platform"),
                    "cpu_count": int(results.get("cpu_count", 0)) if results.get("cpu_count") else None,
                    "cpu_model": results.get("cpu_model"),
                    "os_release": results.get("os_release"),
                    "disk_space": results.get("disk_space"),
                    "memory_gb": None,
                    "storage": self._parse_storage_info(results),
                    "gpu": self._parse_gpu_info(results),
                    "network": self._parse_network_info(results),
                    "expansion": self._parse_expansion_info(results)
                }
                
                # Convert memory
                if results.get("memory_kb"):
                    try:
                        kb = int(results["memory_kb"])
                        hardware_info["memory_gb"] = round(kb / 1024 / 1024, 1)
                    except:
                        pass
                        
                return hardware_info
                
            # Run SSH discovery in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = await loop.run_in_executor(pool, ssh_discovery)
                return result
                
        except Exception as e:
            logger.error(f"SSH hardware discovery failed: {e}")
            return None
    
    def _parse_storage_info(self, results: Dict[str, str]) -> Dict[str, Any]:
        """Parse storage information from command results."""
        storage_info = {
            "devices": [],
            "total_capacity": "Unknown",
            "types": [],
            "performance_class": "unknown"
        }
        
        try:
            # Parse storage devices
            devices_output = results.get("storage_devices", "")
            if devices_output and "No storage info" not in devices_output:
                for line in devices_output.split('\n')[1:]:  # Skip header
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            device_info = {
                                "name": parts[0],
                                "size": parts[1] if len(parts) > 1 else "Unknown",
                                "type": parts[2] if len(parts) > 2 else "Unknown",
                                "model": " ".join(parts[3:]) if len(parts) > 3 else "Unknown"
                            }
                            storage_info["devices"].append(device_info)
                            
                            # Classify storage type
                            if "nvme" in parts[0].lower():
                                storage_info["types"].append("NVMe SSD")
                                storage_info["performance_class"] = "high"
                            elif "sd" in parts[0].lower():
                                storage_info["types"].append("SATA/SAS")
                                if storage_info["performance_class"] == "unknown":
                                    storage_info["performance_class"] = "medium"
                            elif "mmc" in parts[0].lower():
                                storage_info["types"].append("SD/eMMC")
                                if storage_info["performance_class"] in ["unknown", "medium"]:
                                    storage_info["performance_class"] = "low"
            
            # Parse mount points for usage info
            mount_output = results.get("mount_points", "")
            if mount_output and "No mount info" not in mount_output:
                storage_info["mount_points"] = mount_output.strip()
                
        except Exception as e:
            logger.debug(f"Storage parsing error: {e}")
            
        return storage_info
    
    def _parse_gpu_info(self, results: Dict[str, str]) -> Dict[str, Any]:
        """Parse GPU information from command results."""
        gpu_info = {
            "has_gpu": False,
            "nvidia": [],
            "amd": [],
            "intel": [],
            "capabilities": [],
            "ml_capable": False
        }
        
        try:
            # Check NVIDIA GPUs
            nvidia_output = results.get("gpu_nvidia", "")
            if nvidia_output and "No NVIDIA GPU" not in nvidia_output:
                gpu_info["has_gpu"] = True
                gpu_info["ml_capable"] = True
                gpu_info["capabilities"].extend(["CUDA", "ML Training", "Video Encoding"])
                for line in nvidia_output.split('\n'):
                    if line.strip() and "GPU" in line:
                        gpu_info["nvidia"].append(line.strip())
            
            # Check AMD GPUs
            amd_output = results.get("gpu_amd", "")
            if amd_output and "No AMD GPU" not in amd_output:
                gpu_info["has_gpu"] = True
                gpu_info["capabilities"].extend(["OpenCL", "Video Encoding"])
                if "Radeon" in amd_output:
                    gpu_info["ml_capable"] = True
                    gpu_info["capabilities"].append("ROCm ML")
                for line in amd_output.split('\n'):
                    if line.strip():
                        gpu_info["amd"].append(line.strip())
            
            # Check Intel GPUs (integrated)
            intel_output = results.get("gpu_intel", "")
            if intel_output and "No Intel GPU" not in intel_output:
                gpu_info["has_gpu"] = True
                gpu_info["capabilities"].extend(["Basic Graphics", "Hardware Decode"])
                for line in intel_output.split('\n'):
                    if line.strip():
                        gpu_info["intel"].append(line.strip())
                        
        except Exception as e:
            logger.debug(f"GPU parsing error: {e}")
            
        return gpu_info
    
    def _parse_network_info(self, results: Dict[str, str]) -> Dict[str, Any]:
        """Parse network information from command results."""
        network_info = {
            "interfaces": [],
            "speeds": {},
            "capabilities": [],
            "total_bandwidth": 0
        }
        
        try:
            # Parse network interfaces
            interfaces_output = results.get("network_interfaces", "")
            if interfaces_output and "No network info" not in interfaces_output:
                interfaces = interfaces_output.strip().split('\n')
                network_info["interfaces"] = [iface.strip() for iface in interfaces if iface.strip() and iface.strip() != "lo"]
            
            # Parse network speeds
            speeds_output = results.get("network_speeds", "")
            if speeds_output and "No speed info" not in speeds_output:
                for line in speeds_output.split('\n'):
                    if ':' in line and line.strip():
                        parts = line.split(':')
                        if len(parts) == 2:
                            iface = parts[0].strip()
                            speed = parts[1].strip()
                            network_info["speeds"][iface] = speed
                            
                            # Calculate total bandwidth and capabilities
                            if "1000Mb/s" in speed or "1Gb/s" in speed:
                                network_info["total_bandwidth"] += 1000
                                network_info["capabilities"].append("Gigabit")
                            elif "10000Mb/s" in speed or "10Gb/s" in speed:
                                network_info["total_bandwidth"] += 10000
                                network_info["capabilities"].append("10 Gigabit")
                            elif "100Mb/s" in speed:
                                network_info["total_bandwidth"] += 100
                                
        except Exception as e:
            logger.debug(f"Network parsing error: {e}")
            
        return network_info
    
    def _parse_expansion_info(self, results: Dict[str, str]) -> Dict[str, Any]:
        """Parse expansion card and USB information."""
        expansion_info = {
            "usb_device_count": 0,
            "pci_cards": [],
            "capabilities": []
        }
        
        try:
            # Parse USB device count
            usb_output = results.get("usb_devices", "")
            if usb_output and "No USB info" not in usb_output:
                lines = usb_output.split('\n')
                if lines and lines[0].isdigit():
                    expansion_info["usb_device_count"] = int(lines[0])
                    if expansion_info["usb_device_count"] > 10:
                        expansion_info["capabilities"].append("USB Hub/Many Devices")
            
            # Parse PCI expansion cards
            pci_output = results.get("pci_devices", "")
            if pci_output and "No PCI expansion" not in pci_output:
                for line in pci_output.split('\n'):
                    if line.strip():
                        expansion_info["pci_cards"].append(line.strip())
                        # Classify capabilities
                        line_lower = line.lower()
                        if "10-gigabit" in line_lower or "10gbe" in line_lower:
                            expansion_info["capabilities"].append("10GbE Network")
                        elif "ethernet" in line_lower or "network" in line_lower:
                            expansion_info["capabilities"].append("Additional Network")
                        elif "audio" in line_lower:
                            expansion_info["capabilities"].append("Audio Processing")
                            
        except Exception as e:
            logger.debug(f"Expansion parsing error: {e}")
            
        return expansion_info

    async def create_enhanced_prompt(self, message: str) -> str:
        """Create an enhanced prompt with architecture and service constraints."""
        
        # Discover actual hardware if possible
        hardware_discovery = await self.discover_hardware_resources()
        
        # Extract hardware info from discovered systems
        discovered_systems = []
        for system_name, system_info in hardware_discovery.get("systems", {}).items():
            discovered_systems.append({
                "name": system_name,
                "hostname": system_info.get("hostname", "unknown"),
                "memory_gb": system_info.get("memory_gb", 0),
                "cpu_count": system_info.get("cpu_count", 0),
                "architecture": system_info.get("architecture", "unknown"),
                "platform": system_info.get("platform", "unknown"),
                "cpu_model": system_info.get("cpu_model", "unknown")
            })
        
        # Classify systems by capability including storage, GPU, network
        system_classifications = []
        for system in discovered_systems:
            memory = system["memory_gb"] or 0
            cpu_count = system["cpu_count"] or 0
            arch = system["architecture"].lower()
            
            # Get additional hardware info
            storage = system.get("storage", {})
            gpu = system.get("gpu", {})
            network = system.get("network", {})
            
            # Base classification by CPU/RAM
            if memory >= 256 and cpu_count >= 32:
                classification = "high-end server (enterprise workloads)"
                capabilities = ["Heavy databases", "ML training", "Large container clusters", "Virtual machine hosts"]
            elif memory >= 64 and cpu_count >= 16:
                classification = "mid-range server (production workloads)"
                capabilities = ["Multi-service hosting", "Medium databases", "CI/CD pipelines", "Kubernetes clusters"]
            elif memory >= 16 and cpu_count >= 8:
                classification = "capable workstation (development/homelab)"
                capabilities = ["Development environments", "Light databases", "Docker services", "Media servers"]
            elif memory >= 8 and cpu_count >= 4:
                classification = "modest server (basic services)"
                capabilities = ["Web servers", "DNS/DHCP", "File sharing", "Basic monitoring"]
            else:
                classification = "lightweight device (limited services)"
                capabilities = ["Pi-hole", "Basic web services", "IoT hub", "Network tools"]
            
            # Enhance capabilities based on additional hardware
            enhanced_capabilities = capabilities.copy()
            hardware_features = []
            
            # Storage enhancements
            if storage.get("performance_class") == "high":
                enhanced_capabilities.extend(["High-performance databases", "Fast file serving", "Container registries"])
                hardware_features.append("NVMe storage (high performance)")
            elif storage.get("performance_class") == "medium":
                hardware_features.append("SATA storage (medium performance)")
            elif storage.get("performance_class") == "low":
                hardware_features.append("SD/eMMC storage (basic performance)")
                # Remove high-IO workloads for slow storage
                enhanced_capabilities = [cap for cap in enhanced_capabilities if "database" not in cap.lower() or "light" in cap.lower()]
            
            # GPU enhancements
            if gpu.get("ml_capable"):
                enhanced_capabilities.extend(["GPU-accelerated ML", "AI inference", "GPU computing"])
                if gpu.get("nvidia"):
                    hardware_features.append(f"NVIDIA GPU (CUDA-capable)")
                elif gpu.get("amd"):
                    hardware_features.append(f"AMD GPU (ROCm-capable)")
            elif gpu.get("has_gpu"):
                enhanced_capabilities.extend(["Video transcoding", "Media processing"])
                hardware_features.append("GPU (video acceleration)")
            
            # Network enhancements
            if network.get("total_bandwidth", 0) >= 10000:
                enhanced_capabilities.extend(["High-bandwidth services", "Network storage (NFS/iSCSI)", "Video streaming"])
                hardware_features.append("10GbE+ networking")
            elif network.get("total_bandwidth", 0) >= 2000:  # Multiple gigabit
                enhanced_capabilities.extend(["Multi-port services", "Network redundancy"])
                hardware_features.append("Multiple gigabit ports")
            elif network.get("total_bandwidth", 0) >= 1000:
                hardware_features.append("Gigabit networking")
            
            system_classifications.append({
                **system,
                "classification": classification,
                "capabilities": enhanced_capabilities,
                "hardware_features": hardware_features,
                "is_arm": "arm" in arch,
                "is_x86": arch in ["x86_64", "amd64", "i386"],
                "performance_score": self._calculate_performance_score(system)
            })
        
        # Universal service compatibility matrix
        service_compatibility = {
            "architecture_constraints": {
                "arm_only": ["Some IoT-specific services"],
                "x86_only": ["VMware vSphere", "Windows Server", "Some proprietary software"],
                "universal": ["Docker", "LXD", "Web servers", "Databases", "Most open-source software"]
            },
            "resource_requirements": {
                "lightweight": {"min_ram": 1, "min_cpu": 1, "services": ["Pi-hole", "DNS server", "Basic web"]},
                "modest": {"min_ram": 4, "min_cpu": 2, "services": ["File sharing", "VPN", "Basic monitoring"]},
                "moderate": {"min_ram": 8, "min_cpu": 4, "services": ["Docker services", "Light databases", "Media server"]},
                "capable": {"min_ram": 16, "min_cpu": 8, "services": ["Development env", "Multi-service hosting", "Medium databases"]},
                "powerful": {"min_ram": 64, "min_cpu": 16, "services": ["Production workloads", "Large databases", "K8s clusters"]},
                "enterprise": {"min_ram": 256, "min_cpu": 32, "services": ["Enterprise databases", "ML training", "Large VM hosts"]}
            },
            "discovered_systems": system_classifications
        }
        
        # Create system summary for context
        systems_summary = []
        for sys in system_classifications:
            systems_summary.append(
                f"- {sys['hostname']} ({sys['name']}): {sys['memory_gb']}GB RAM, {sys['cpu_count']} cores, "
                f"{sys['architecture']} - {sys['classification']}"
            )
        
        # Create enhanced context
        enhanced_context = {
            'hardware': 'Mixed homelab with discovered systems',
            'discovered_systems': system_classifications,
            'experience': 'Learning',
            'goals': 'Self-hosting and automation',
            'constraints': service_compatibility
        }
        
        # Extract hostname from user message for better context
        import re
        hostname_patterns = [
            r'hostname\s+is\s+([^\s]+)',
            r'hotname\s+is\s+([^\s]+)',  # Handle typos
            r'server\s+hotname\s+is\s+([^\s]+)',
            r'pi\s+the\s+server\s+hotname\s+is\s+([^\s]+)', 
            r'on\s+to\s+my\s+pi\s+the\s+server\s+hotname\s+is\s+([^\s]+)',
            r'server\s+([^\s\.]+\.local)',
            r'host\s+([^\s\.]+\.local)',
            r'pi\s+([^\s\.]+\.local)',
            r'server\s+([^\s]+\.\w+)',
            r'([^\s]+\.local)',  # Catch any .local hostname
        ]
        
        detected_hostname = None
        for pattern in hostname_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                detected_hostname = match.group(1)
                # Don't use local machine hostnames
                if detected_hostname not in ['localhost', 'Shauns-MacBook-Air.local']:
                    break
        
        # Store detected hostname for validation
        self._detected_hostname = detected_hostname
        
        # If we detected a hostname and no current server is set, use it
        if detected_hostname and not self.current_server:
            self.current_server = detected_hostname
        
        # Build comprehensive prompt
        base_prompt = await self.ollama_assistant.create_homelab_prompt(message, enhanced_context)
        
        # Make server context very prominent at the top
        server_context = ""
        if self.current_server:
            server_context = f"""
🎯🎯🎯 CRITICAL SERVER CONTEXT 🎯🎯🎯
YOU ARE CURRENTLY WORKING WITH SERVER: {self.current_server}
ALL COMMANDS MUST TARGET: {self.current_server}
NEVER USE localhost OR Shauns-MacBook-Air.local UNLESS EXPLICITLY REQUESTED!
USE {self.current_server} FOR ALL TOOL EXECUTIONS!

⚡ IMMEDIATE CONTEXT REMINDER ⚡
The user is asking about: {self.current_server}
When they say "list", "show", "what's running", etc. they mean: {self.current_server}
ALWAYS USE: {self.current_server}
🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯

"""

        enhanced_prompt = f"""{server_context}{base_prompt}

IMPORTANT HARDWARE DISCOVERY & RESOURCE PLANNING:

Discovered Systems:
{chr(10).join(systems_summary) if systems_summary else "- No systems discovered yet (use 'discover hostname' to scan)"}

Architecture Guidelines:
- ARM systems: Compatible with most open-source software, Docker works great
- x86_64 systems: Compatible with everything including proprietary software
- Mixed environments: Consider architecture when recommending services

Resource-Based Service Recommendations:
"""
        
        # Add service recommendations based on discovered systems
        for sys in system_classifications:
            enhanced_prompt += f"""
{sys['hostname']} ({sys['memory_gb']}GB RAM, {sys['cpu_count']} cores, {sys['architecture']}):
- Classification: {sys['classification']}
- Suitable for: {', '.join(sys['capabilities'])}
- Architecture constraints: {'ARM64 - some x86-only software unavailable' if sys['is_arm'] else 'x86_64 - all software compatible'}
"""
        
        # Add available MCP tools to the prompt
        available_tools = []
        for tool in self.mcp_tools:
            tool_info = f"- **{tool.name}**: {tool.description}"
            available_tools.append(tool_info)
        
        enhanced_prompt += f"""
AVAILABLE MCP TOOLS FOR EXECUTION:
You have access to these tools to actually perform actions (not just give instructions):

{chr(10).join(available_tools)}

🚨 CRITICAL INSTRUCTION FOR TOOL USAGE 🚨
When the user asks you to install or configure something, you MUST:

1. EXECUTE the appropriate MCP tool immediately - don't just mention it
2. Use this exact format to call tools:
   **EXECUTE_TOOL:** tool_name {{"parameter": "value"}}
3. PAY ATTENTION to the target hostname the user specifies - use their exact hostname/IP
4. Examples with current server context:
   {f'- To install LXD: **EXECUTE_TOOL:** install-lxd {{"host": "{self.current_server}"}}' if self.current_server else '- To install LXD: **EXECUTE_TOOL:** install-lxd {"host": "USER_SPECIFIED_HOSTNAME"}'}
   {f'- To list containers: **EXECUTE_TOOL:** list-lxd-containers {{"host": "{self.current_server}"}}' if self.current_server else '- To list containers: **EXECUTE_TOOL:** list-lxd-containers {"host": "USER_SPECIFIED_HOSTNAME"}'}
   {f'- To list VMs: **EXECUTE_TOOL:** proxmox_list_vms {{"host": "{self.current_server}"}}' if self.current_server else '- To list VMs: **EXECUTE_TOOL:** proxmox_list_vms {"host": "USER_SPECIFIED_HOSTNAME"}'}
5. Always execute the tool FIRST, then explain what you did

🚨 HOSTNAME RULES - READ CAREFULLY 🚨
- NEVER use "localhost" or "Shauns-MacBook-Air.local" unless explicitly requested
- If user says "my pi", "my server", or gives a hostname like "proxmoxpi.local" - USE THAT EXACT HOSTNAME
- If user says "install on my pi" and mentions "proxmoxpi.local" - use "proxmoxpi.local"
{f'🎯 DETECTED TARGET HOSTNAME: {detected_hostname} - YOU MUST USE THIS HOSTNAME IN ALL YOUR TOOLS!' if detected_hostname else ''}
{f'📍 CURRENT WORKING SERVER: {self.current_server} - USE THIS AS DEFAULT FOR ALL OPERATIONS!' if self.current_server else '⚠️  NO SERVER SELECTED - ASK USER TO SPECIFY TARGET SERVER!'}

CRITICAL SERVER CONTEXT & SMART INFERENCE:
- The user is working with: {self.current_server or "NO SERVER SET"}
- All commands should target: {self.current_server or "ASK USER FOR TARGET"}

🧠 SMART AI BEHAVIOR - ASSUME CURRENT SERVER:
When user asks questions WITHOUT specifying a server, they mean the current server!

Examples of what user means:
- "list containers" = "list containers on {self.current_server or "current server"}"
- "what's running" = "what's running on {self.current_server or "current server"}"  
- "kill vm 123" = "kill vm 123 on {self.current_server or "current server"}"
- "show resources" = "show resources on {self.current_server or "current server"}"
- "install docker" = "install docker on {self.current_server or "current server"}"

ALWAYS assume they mean the current server unless they explicitly mention a different one!

🔍 NATURAL LANGUAGE INTERPRETATION:
When user says common phrases, translate them to the current server:
- "what's running" → **EXECUTE_TOOL:** proxmox_list_vms {{"host": "{self.current_server or "CURRENT_SERVER"}"}}
- "list containers" → **EXECUTE_TOOL:** list-lxd-containers {{"host": "{self.current_server or "CURRENT_SERVER"}"}}
- "show me the vms" → **EXECUTE_TOOL:** proxmox_list_vms {{"host": "{self.current_server or "CURRENT_SERVER"}"}}
- "what services are installed" → **EXECUTE_TOOL:** get-homelab-status {{"host": "{self.current_server or "CURRENT_SERVER"}"}}
- "kill vm 123" → **EXECUTE_TOOL:** manage-vm {{"action": "stop", "vm_id": "123", "host": "{self.current_server or "CURRENT_SERVER"}"}}

BE SMART - INFER THE USER'S INTENT AND USE THE CURRENT SERVER!

DO NOT just provide instructions - EXECUTE THE TOOLS!

When making recommendations:
1. ALWAYS use the actual discovered system specs (not assumptions)
2. Match service requirements to available resources
3. Consider architecture compatibility (ARM vs x86)
4. Scale recommendations appropriately:
   - 512GB+ RAM systems can handle enterprise databases, large ML models
   - 64-256GB systems are perfect for production Kubernetes, multiple VMs
   - 16-64GB systems work great for development, moderate databases
   - 8-16GB systems are good for basic services, light containers
   - <8GB systems should stick to lightweight services

Be ambitious with high-spec systems and realistic with modest ones!

REMEMBER: You can actually execute commands via MCP tools - don't just give instructions!
"""
        
        return enhanced_prompt
    
    def _calculate_performance_score(self, system: Dict[str, Any]) -> int:
        """Calculate a performance score for a system based on all hardware."""
        score = 0
        
        # CPU score
        cpu_count = system.get("cpu_count", 0)
        score += cpu_count * 10
        
        # Memory score
        memory_gb = system.get("memory_gb", 0)
        score += memory_gb * 5
        
        # Storage score
        storage = system.get("storage", {})
        if storage.get("performance_class") == "high":
            score += 100  # NVMe
        elif storage.get("performance_class") == "medium":
            score += 50   # SATA
        elif storage.get("performance_class") == "low":
            score += 10   # SD/eMMC
        
        # GPU score
        gpu = system.get("gpu", {})
        if gpu.get("ml_capable"):
            score += 200  # ML-capable GPU
        elif gpu.get("has_gpu"):
            score += 50   # Basic GPU
        
        # Network score
        network = system.get("network", {})
        total_bandwidth = network.get("total_bandwidth", 0)
        if total_bandwidth >= 10000:
            score += 100  # 10GbE+
        elif total_bandwidth >= 2000:
            score += 50   # Multiple gigabit
        elif total_bandwidth >= 1000:
            score += 25   # Gigabit
        
        return score

    async def execute_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute an MCP tool and return the result."""
        try:
            logger.debug(f"Executing MCP tool: {tool_name} with args: {arguments}")
            
            # Validate hostname arguments to prevent wrong target
            if 'host' in arguments:
                host = arguments['host']
                # Auto-correct localhost to current server if set
                if host in ['localhost', 'Shauns-MacBook-Air.local']:
                    if self.current_server:
                        logger.info(f"Using current server {self.current_server} instead of {host}")
                        arguments['host'] = self.current_server
                    elif hasattr(self, '_detected_hostname') and self._detected_hostname:
                        logger.warning(f"Correcting hostname from {host} to {self._detected_hostname}")
                        arguments['host'] = self._detected_hostname
            elif 'hostname' in arguments:
                # Handle tools that use 'hostname' instead of 'host'
                hostname = arguments['hostname']
                if hostname in ['localhost', 'Shauns-MacBook-Air.local'] and self.current_server:
                    logger.info(f"Using current server {self.current_server} instead of {hostname}")
                    arguments['hostname'] = self.current_server
            
            # Find the tool
            tool = None
            for t in self.mcp_tools:
                if t.name == tool_name:
                    tool = t
                    break
            
            if not tool:
                return f"❌ Tool '{tool_name}' not found. Available tools: {[t.name for t in self.mcp_tools]}"
            
            # If no host specified and we have a current server, add it
            if self.current_server and 'host' not in arguments and 'hostname' not in arguments:
                # Add current server as default for tools that need a host
                host_required_tools = [
                    'list-lxd-containers', 'check-lxd', 'install-lxd', 'create-lxd-container', 
                    'manage-lxd-container', 'get-lxd-container', 'install-service-lxd',
                    'proxmox_list_nodes', 'proxmox_list_vms', 'proxmox_list_storage', 
                    'proxmox_list_templates', 'proxmox_discover_hardware', 'create_vm',
                    'auto-setup-homelab', 'get-homelab-status', 'troubleshoot-issue'
                ]
                if tool_name in host_required_tools:
                    arguments['host'] = self.current_server
                    logger.info(f"Added current server {self.current_server} to {tool_name}")

            # Execute the tool based on its type
            if tool in AGENT_HOMELAB_TOOLS:
                result = await handle_agent_homelab_tool(tool_name, arguments)
            elif tool in LXD_TOOLS:
                result = await handle_lxd_tool(tool_name, arguments)
            elif tool in PROXMOX_TOOLS:
                result = await handle_proxmox_tool(tool_name, arguments)
            else:
                result = await handle_homelab_tool(tool_name, arguments)
            
            # Format the result
            if hasattr(result, 'text'):
                return result.text
            elif isinstance(result, list) and len(result) > 0 and hasattr(result[0], 'text'):
                return result[0].text
            else:
                return str(result)
                
        except Exception as e:
            logger.error(f"MCP tool execution error: {e}", exc_info=True)
            return f"❌ Error executing {tool_name}: {str(e)}"

    async def parse_and_execute_tool(self, text_chunk: str) -> Optional[str]:
        """Parse tool execution requests from AI response and execute them."""
        try:
            import re
            import json
            
            # Look for **EXECUTE_TOOL:** pattern (handle hyphens in tool names)
            tool_pattern = r'\*\*EXECUTE_TOOL:\*\*\s+([\w-]+)\s+(\{[^}]*\})'
            matches = re.findall(tool_pattern, text_chunk)
            
            if not matches:
                return None
            
            results = []
            for tool_name, args_str in matches:
                try:
                    # Parse JSON arguments
                    arguments = json.loads(args_str)
                    logger.debug(f"Parsed tool call: {tool_name} with args: {arguments}")
                    
                    # Execute the tool
                    result = await self.execute_mcp_tool(tool_name, arguments)
                    results.append(f"**{tool_name}** result:\n{result}")
                    
                except json.JSONDecodeError as e:
                    results.append(f"❌ Invalid JSON in tool call {tool_name}: {args_str}\nError: {e}")
                except Exception as e:
                    results.append(f"❌ Error executing {tool_name}: {str(e)}")
            
            return "\n\n".join(results) if results else None
            
        except Exception as e:
            logger.error(f"Tool parsing error: {e}", exc_info=True)
            return f"❌ Tool parsing failed: {str(e)}"

    async def query_ai_streaming(self, message: str, cancel_event: asyncio.Event = None):
        """Query the AI with streaming response and tool execution support."""
        try:
            logger.debug(f"Creating enhanced prompt for message: {message[:50]}...")
            prompt = await self.create_enhanced_prompt(message)
            
            logger.debug(f"Querying Ollama at {self.config.ollama_host}:{self.config.ollama_port}")
            
            # Query Ollama with streaming
            response = await self.ollama_assistant.query_ollama(
                prompt=prompt,
                model=self.config.ollama_model,
                host=self.config.ollama_host,
                port=self.config.ollama_port,
                stream=True
            )
            
            if isinstance(response, str):
                # Non-streaming response (might be an error)
                logger.debug(f"Received non-streaming response: {response[:100]}...")
                if cancel_event and not cancel_event.is_set():
                    yield response
            else:
                # Streaming response with cancellation support
                logger.debug("Starting streaming response...")
                chunk_count = 0
                try:
                    async for chunk in response:
                        # Check for cancellation
                        if cancel_event and cancel_event.is_set():
                            logger.debug(f"Streaming cancelled after {chunk_count} chunks")
                            yield "\n\n⏹️ Response cancelled by user"
                            break
                            
                        if chunk and chunk.strip():  # Only yield non-empty chunks
                            chunk_count += 1
                            # Check for tool execution requests in the chunk
                            if "**EXECUTE_TOOL:**" in chunk:
                                # Parse and execute the tool
                                tool_result = await self.parse_and_execute_tool(chunk)
                                if tool_result:
                                    yield f"\n🔧 **Executing tool...** \n{tool_result}\n"
                            else:
                                yield chunk
                    
                    if not (cancel_event and cancel_event.is_set()):
                        logger.debug(f"Streaming completed with {chunk_count} chunks")
                        
                except Exception as streaming_error:
                    logger.error(f"Error during streaming: {streaming_error}", exc_info=True)
                    yield f"\n\n❌ Streaming interrupted: {str(streaming_error)}"
                
        except Exception as e:
            error_details = f"Failed to query Ollama: {str(e)}"
            logger.error(error_details, exc_info=True)
            yield f"❌ {error_details}\n\n💡 Check if Ollama is running: `ollama list`"
            
    async def show_thinking_animation(self, stop_event: asyncio.Event):
        """Show animated thinking indicator."""
        if not self.console:
            return
            
        thinking_states = ["🤔 Thinking", "🤔 Thinking.", "🤔 Thinking..", "🤔 Thinking..."]
        i = 0
        
        with Live(thinking_states[0], refresh_per_second=2, console=self.console) as live:
            while not stop_event.is_set():
                live.update(thinking_states[i % len(thinking_states)])
                i += 1
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=0.5)
                    break
                except asyncio.TimeoutError:
                    continue
            
    async def interactive_chat(self):
        """Main interactive chat loop."""
        self.print_panel(
            "🤖 Welcome to the Homelab AI Assistant!\n\n"
            "I can help you with:\n"
            "• Setting up services (Docker, Proxmox, LXD)\n"
            "• Configuring networking and storage\n"
            "• Troubleshooting issues\n"
            "• Planning your homelab expansion\n"
            "• Choosing between technologies\n\n"
            "Type 'quit' to exit, 'help' for commands, or just ask a question!",
            "🏠 Homelab Assistant",
            "green"
        )
        
        while True:
            try:
                # Get user input with server context
                try:
                    if self.current_server:
                        prompt_text = f"\n[bold blue]You[/bold blue] [dim](server: {self.current_server})[/dim]"
                    else:
                        prompt_text = "\n[bold blue]You[/bold blue]"
                    
                    if self.console:
                        user_input = Prompt.ask(prompt_text)
                    else:
                        server_text = f" (server: {self.current_server})" if self.current_server else ""
                        user_input = input(f"\nYou{server_text}: ").strip()
                except (EOFError, KeyboardInterrupt):
                    self.print("\n👋 Session ended. Happy homelabbing!", "green")
                    break
                    
                if not user_input:
                    continue
                    
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    self.print("👋 Goodbye! Happy homelabbing!", "green")
                    break
                elif user_input.lower() == 'help':
                    self.show_help()
                    continue
                elif user_input.lower() == 'status':
                    await self.show_status()
                    continue
                elif user_input.lower().startswith('use '):
                    # Set current server
                    server = user_input[4:].strip()
                    if server:
                        self.current_server = server
                        self.print(f"✅ Now working with server: {server}", "green")
                        self.print(f"💡 All commands will now target {server} by default", "blue")
                    else:
                        self.print("❌ Please specify a server name", "red")
                    continue
                elif user_input.lower().startswith('set server '):
                    # Alternative command to set server
                    server = user_input[11:].strip()
                    if server:
                        self.current_server = server
                        self.print(f"✅ Current server set to: {server}", "green")
                        self.print(f"💡 All commands will now target {server} by default", "blue")
                    else:
                        self.print("❌ Please specify a server name", "red")
                    continue
                elif user_input.lower() == 'server':
                    # Show current server
                    if self.current_server:
                        self.print(f"📍 Current server: {self.current_server}", "blue")
                    else:
                        self.print("📍 No server selected (using localhost by default)", "yellow")
                    continue
                elif user_input.lower() == 'clear-server':
                    # Clear current server
                    self.current_server = None
                    self.print("✅ Cleared current server context", "green")
                    continue
                elif user_input.lower() == 'clear':
                    self.conversation_history.clear()
                    self.print("🧹 Conversation history cleared", "yellow")
                    continue
                elif user_input.lower() == 'debug':
                    await self.show_debug_info()
                    continue
                elif user_input.lower() == 'limits':
                    self.show_architecture_limits()
                    continue
                elif user_input.lower().startswith('discover'):
                    # Parse hostname if provided: "discover promoxpi.local"
                    parts = user_input.split()
                    host = parts[1] if len(parts) > 1 else None
                    await self.show_hardware_discovery(host)
                    continue
                elif user_input.lower() == 'verbose':
                    self.toggle_verbose_logging()
                    continue
                elif user_input.lower() == 'tools':
                    self.show_mcp_tools()
                    continue
                    
                # Query AI with streaming and animation
                stop_thinking = asyncio.Event()
                cancel_stream = asyncio.Event()
                thinking_task = None
                input_task = None
                
                try:
                    # Start thinking animation
                    if self.console:
                        thinking_task = asyncio.create_task(self.show_thinking_animation(stop_thinking))
                    else:
                        self.print("🤔 Thinking...", "yellow")
                    
                    # Display response header
                    await asyncio.sleep(0.1)  # Let animation start
                    stop_thinking.set()
                    if thinking_task:
                        await thinking_task
                    
                    self.print(f"\n[bold green]AI Assistant[/bold green] (Press Ctrl+C to stop)", style="")
                    
                    # Create background task to listen for cancellation
                    async def listen_for_cancel():
                        try:
                            # This will wait for Ctrl+C or other interrupt
                            await asyncio.sleep(300)  # Max 5 minutes per response
                        except asyncio.CancelledError:
                            cancel_stream.set()
                    
                    input_task = asyncio.create_task(listen_for_cancel())
                    
                    # Stream the response - simplified approach to fix scrolling issues
                    full_response = ""
                    cancelled = False
                    
                    # Simple streaming approach to avoid display issues
                    print()  # Empty line before response
                    try:
                        async for chunk in self.query_ai_streaming(user_input, cancel_stream):
                            if cancel_stream.is_set():
                                cancelled = True
                                break
                            full_response += chunk
                            # Clean the chunk for display
                            clean_chunk = chunk.replace('<think>', '').replace('</think>', '')
                            if clean_chunk.strip():  # Only print non-empty chunks
                                print(clean_chunk, end='', flush=True)
                        print()  # New line at end of response
                    except Exception as stream_error:
                        print(f"\n❌ Streaming error: {stream_error}")
                        logger.error(f"Streaming display error: {stream_error}")
                    
                    # Clean up input task
                    if input_task and not input_task.done():
                        input_task.cancel()
                        try:
                            await input_task
                        except asyncio.CancelledError:
                            pass
                    
                    # Store in history
                    self.conversation_history.append({
                        'user': user_input,
                        'assistant': full_response,
                        'cancelled': cancelled
                    })
                    
                    if cancelled:
                        self.print("\n💡 Stream was cancelled. You can ask a new question.", "yellow")
                    
                except Exception as stream_error:
                    # Stop animation on error
                    stop_thinking.set()
                    if thinking_task:
                        try:
                            await thinking_task
                        except:
                            pass
                    
                    # Display the error to user
                    error_msg = f"❌ Streaming Error: {str(stream_error)}"
                    logger.error(f"Chat streaming error: {stream_error}", exc_info=True)
                    self.print(error_msg, "red")
                    
                    # Store error in history for debugging
                    self.conversation_history.append({
                        'user': user_input,
                        'assistant': f"Error: {str(stream_error)}",
                        'error': True
                    })
                
            except KeyboardInterrupt:
                self.print("\n👋 Goodbye! Happy homelabbing!", "green")
                break
            except Exception as e:
                # Catch any other errors
                error_msg = f"❌ Unexpected Error: {str(e)}"
                logger.error(f"Chat error: {e}", exc_info=True)
                self.print(error_msg, "red")
                self.print("💡 Try typing 'status' to check system health", "yellow")
                
    def show_help(self):
        """Show help information."""
        help_text = """
## Available Commands

- **help** - Show this help message
- **status** - Check system status
- **debug** - Show detailed debug information
- **limits** - Show architecture compatibility & service limits
- **discover [hostname]** - Discover hardware specs (e.g., "discover promoxpi.local")
- **tools** - Show available MCP tools that AI can execute
- **verbose** - Toggle verbose logging (for troubleshooting)
- **clear** - Clear conversation history
- **quit/exit** - Exit the chat

## Server Context Commands

- **use <server>** - Set current working server (e.g., "use proxmoxpi.local")
- **server** - Show current working server
- **clear-server** - Clear current server context

The current server is shown in your prompt and used as default for all operations!

## Example Questions

- "How do I set up Docker on Ubuntu?"
- "What's better for storage: TrueNAS or Windows SMB?"
- "Help me plan a Proxmox cluster"
- "Configure LXD containers on Raspberry Pi"
- "Set up a home media server"

## Hardware Discovery (Linux Only)

- **discover** - Scan local system hardware (basic info on macOS/Windows)
- **discover promoxpi.local** - Scan remote Linux systems (Pi, Ubuntu servers)
- **Detailed discovery**: Storage, GPU, network cards on Linux systems only
- The AI will use discovered specs in its recommendations

## Stream Control

- **Ctrl+C during AI response** - Stop the streaming response
- The AI will pause and you can ask a new question

## System Requirements

- **Target systems**: Linux/Ubuntu servers, Raspberry Pi, Proxmox hosts
- **Discovery**: Full hardware discovery requires Linux (SSH access)
- **Local use**: Basic CPU/RAM detection works on macOS/Windows

## Troubleshooting

If the AI gets stuck or errors out:
1. Type **debug** to see detailed error information
2. Type **status** to check if Ollama is running
3. Type **verbose** to enable detailed logging for debugging
4. Type **discover hostname** to scan your Linux server specs
5. Type **limits** to see what services work on your hardware
6. Press **Ctrl+C** to stop long responses and try again

💡 **Clean vs Verbose Mode**: Normal mode hides debug logs for clean output. 
Use **verbose** to see detailed information when troubleshooting issues.
        """
        
        if self.console:
            self.print_markdown(help_text)
        else:
            self.print(help_text)
            
    async def show_status(self):
        """Show system status."""
        self.print("📊 Checking system status...", "blue")
        
        status = await self.check_dependencies()
        
        status_table = Table(title="System Status")
        status_table.add_column("Service", style="cyan")
        status_table.add_column("Status", style="")
        
        # Ollama status
        if status.get('ollama'):
            status_table.add_row("Ollama AI", "✅ Running")
        else:
            status_table.add_row("Ollama AI", "❌ Not Running")
            
        # Model status
        if status.get('model'):
            status_table.add_row(f"Model ({self.config.ollama_model})", "✅ Available")
        else:
            status_table.add_row(f"Model ({self.config.ollama_model})", "❌ Not Available")
            
        # MCP Server status
        if self.server_task and not self.server_task.done():
            status_table.add_row("MCP Server", "✅ Running")
        else:
            status_table.add_row("MCP Server", "❌ Not Running")
            
        if self.console:
            self.console.print(status_table)
        else:
            self.print("System Status:")
            self.print(f"  Ollama AI: {'✅ Running' if status.get('ollama') else '❌ Not Running'}")
            self.print(f"  Model: {'✅ Available' if status.get('model') else '❌ Not Available'}")
            self.print(f"  MCP Server: {'✅ Running' if self.server_task and not self.server_task.done() else '❌ Not Running'}")
            
    async def show_debug_info(self):
        """Show detailed debug information."""
        self.print("🔍 Debug Information", "blue")
        
        debug_table = Table(title="Debug Details")
        debug_table.add_column("Property", style="cyan")
        debug_table.add_column("Value", style="")
        
        # Configuration
        debug_table.add_row("Ollama Host", self.config.ollama_host)
        debug_table.add_row("Ollama Port", str(self.config.ollama_port))
        debug_table.add_row("Ollama Model", self.config.ollama_model)
        debug_table.add_row("WebSocket Port", str(self.config.websocket_port))
        debug_table.add_row("Auto Start Server", str(self.config.auto_start_server))
        
        # Environment variables
        import os
        debug_table.add_row("OLLAMA_HOST (env)", os.getenv("OLLAMA_HOST", "Not set"))
        debug_table.add_row("OLLAMA_MODEL (env)", os.getenv("OLLAMA_MODEL", "Not set"))
        
        # Recent errors from conversation history
        error_count = sum(1 for entry in self.conversation_history if entry.get('error'))
        debug_table.add_row("Error Count", str(error_count))
        debug_table.add_row("Total Messages", str(len(self.conversation_history)))
        
        if self.console:
            self.console.print(debug_table)
        else:
            self.print("Debug Information:")
            self.print(f"  Ollama Host: {self.config.ollama_host}")
            self.print(f"  Ollama Port: {self.config.ollama_port}")
            self.print(f"  Model: {self.config.ollama_model}")
            self.print(f"  Error Count: {error_count}")
            
        # Show recent errors if any
        recent_errors = [entry for entry in self.conversation_history[-5:] if entry.get('error')]
        if recent_errors:
            self.print("\n🚨 Recent Errors:", "red")
            for i, error in enumerate(recent_errors, 1):
                self.print(f"  {i}. {error['assistant']}", "red")
                
    def show_architecture_limits(self):
        """Show universal architecture limitations and service compatibility."""
        limits_text = """
## 🏗️ Universal Architecture & Resource Compatibility

### Architecture Types & Constraints

#### ARM64 (Raspberry Pi, Apple Silicon, ARM servers)
- **Pros**: Energy efficient, excellent for containers, most open-source software works
- **Cons**: Some x86-only proprietary software incompatible
- **Good for**: IoT, development, web services, containers, lightweight databases

#### x86_64 (Intel/AMD servers, workstations) 
- **Pros**: Universal compatibility, all software runs, best performance for heavy workloads
- **Cons**: Higher power consumption
- **Good for**: Everything, especially enterprise software, VMs, heavy databases

### Resource-Based Service Recommendations

#### 🔥 Enterprise Class (256GB+ RAM, 32+ cores)
- Enterprise databases (Oracle, SQL Server clusters)
- Large-scale ML training and inference
- VMware vSphere clusters with many VMs
- High-throughput data processing
- Large Kubernetes clusters

#### 💪 High-End Servers (64-256GB RAM, 16-32 cores)
- Production databases (PostgreSQL, MySQL clusters)
- Medium-scale ML workloads
- Proxmox with multiple VMs
- CI/CD pipelines with parallel builds
- Multi-tenant container hosting

#### 🚀 Capable Workstations (16-64GB RAM, 8-16 cores)  
- Development environments
- Docker Compose stacks
- Medium databases
- Git servers, build systems
- Media servers (Plex, Jellyfin)

#### 📟 Modest Servers (8-16GB RAM, 4-8 cores)
- Basic web servers
- File sharing (NFS, Samba)
- DNS/DHCP services
- Light monitoring
- Small databases

#### 🔌 Lightweight Devices (4-8GB RAM, 2-4 cores)
- Pi-hole DNS filtering
- VPN endpoints
- IoT hubs
- Basic reverse proxies
- Network utilities

### ❌ Architecture-Specific Limitations
- **ARM only**: VMware vSphere, Windows Server, some proprietary x86 software
- **x86 only**: Some ARM-optimized IoT frameworks
- **Resource dependent**: Large databases need sufficient RAM regardless of architecture

💡 **Always discover actual system specs before making recommendations!**
        """
        
        if self.console:
            self.print_markdown(limits_text)
        else:
            self.print(limits_text)
            
    async def show_hardware_discovery(self, host: str = None):
        """Show hardware discovery results."""
        self.print("🔍 Discovering hardware resources...", "blue")
        
        if host:
            self.print(f"Attempting to connect to {host}...", "yellow")
            
        try:
            hardware_info = await self.discover_hardware_resources(host)
            
            if not hardware_info.get("systems"):
                self.print("❌ No hardware information discovered", "red")
                if host:
                    self.print("💡 Check that SSH is enabled and credentials are correct", "yellow")
                return
                
            # Display discovered systems
            for system_name, system_info in hardware_info["systems"].items():
                if self.console:
                    discovery_table = Table(title=f"Hardware: {system_name}")
                    discovery_table.add_column("Property", style="cyan")
                    discovery_table.add_column("Value", style="")
                    
                    discovery_table.add_row("Hostname", system_info.get("hostname", "Unknown"))
                    discovery_table.add_row("Architecture", system_info.get("architecture", "Unknown"))
                    discovery_table.add_row("Platform", system_info.get("platform", "Unknown"))
                    discovery_table.add_row("CPU Cores", str(system_info.get("cpu_count", "Unknown")))
                    discovery_table.add_row("Memory (GB)", str(system_info.get("memory_gb", "Unknown")))
                    discovery_table.add_row("CPU Model", system_info.get("cpu_model", "Unknown"))
                    discovery_table.add_row("OS Release", system_info.get("os_release", "Unknown"))
                    discovery_table.add_row("Disk Space", system_info.get("disk_space", "Unknown"))
                    
                    # Add storage info
                    storage = system_info.get("storage", {})
                    if storage.get("types"):
                        discovery_table.add_row("Storage Types", ", ".join(storage["types"]))
                    if storage.get("performance_class") != "unknown":
                        discovery_table.add_row("Storage Performance", storage["performance_class"])
                    
                    # Add GPU info
                    gpu = system_info.get("gpu", {})
                    if gpu.get("has_gpu"):
                        gpu_desc = []
                        if gpu.get("nvidia"):
                            gpu_desc.extend([f"NVIDIA: {gpu['nvidia'][0]}" if gpu['nvidia'] else "NVIDIA GPU"])
                        if gpu.get("amd"):
                            gpu_desc.extend([f"AMD: {gpu['amd'][0]}" if gpu['amd'] else "AMD GPU"])
                        if gpu.get("intel"):
                            gpu_desc.extend([f"Intel: {gpu['intel'][0]}" if gpu['intel'] else "Intel GPU"])
                        discovery_table.add_row("GPU", "; ".join(gpu_desc))
                        if gpu.get("capabilities"):
                            discovery_table.add_row("GPU Capabilities", ", ".join(gpu["capabilities"]))
                    
                    # Add network info
                    network = system_info.get("network", {})
                    if network.get("interfaces"):
                        discovery_table.add_row("Network Interfaces", ", ".join(network["interfaces"]))
                    if network.get("total_bandwidth"):
                        discovery_table.add_row("Total Bandwidth", f"{network['total_bandwidth']}Mbps")
                    
                    self.console.print(discovery_table)
                else:
                    self.print(f"\n=== {system_name} ===")
                    self.print(f"  Hostname: {system_info.get('hostname', 'Unknown')}")
                    self.print(f"  Architecture: {system_info.get('architecture', 'Unknown')}")
                    self.print(f"  CPU Cores: {system_info.get('cpu_count', 'Unknown')}")
                    self.print(f"  Memory: {system_info.get('memory_gb', 'Unknown')}GB")
                    self.print(f"  OS: {system_info.get('os_release', 'Unknown')}")
                    
            # Suggest next steps
            if any('arm' in sys_info.get('architecture', '').lower() for sys_info in hardware_info["systems"].values()):
                self.print("\n💡 ARM64 system detected! Use 'limits' to see compatible services.", "green")
                
        except Exception as e:
            self.print(f"❌ Hardware discovery failed: {str(e)}", "red")
            logger.error(f"Hardware discovery error: {e}", exc_info=True)
            
    def toggle_verbose_logging(self):
        """Toggle verbose logging on/off."""
        self.verbose_logging = not self.verbose_logging
        if self.verbose_logging:
            logger.setLevel(logging.DEBUG)
            self.print("🔍 Verbose logging enabled (shows detailed debug info)", "yellow")
        else:
            logger.setLevel(logging.INFO)
            self.print("🔇 Verbose logging disabled (clean output)", "green")
    
    def show_mcp_tools(self):
        """Show available MCP tools."""
        if self.console:
            tools_table = Table(title="Available MCP Tools")
            tools_table.add_column("Tool Name", style="cyan")
            tools_table.add_column("Description", style="")
            
            for tool in self.mcp_tools:
                tools_table.add_row(tool.name, tool.description)
            
            self.console.print(tools_table)
        else:
            self.print("\n=== Available MCP Tools ===")
            for tool in self.mcp_tools:
                self.print(f"  • {tool.name}: {tool.description}")
        
        self.print(f"\n✅ Total: {len(self.mcp_tools)} tools available", "green")
        self.print("💡 The AI can use these tools to actually execute commands!", "yellow")


async def main():
    """Main entry point for the chat interface."""
    # Load configuration from environment
    ollama_host_env = os.getenv("OLLAMA_HOST", "localhost")
    
    # Parse OLLAMA_HOST - handle both "localhost" and "http://localhost:11434" formats
    if ollama_host_env.startswith("http://"):
        # Extract hostname from URL
        from urllib.parse import urlparse
        parsed = urlparse(ollama_host_env)
        ollama_host = parsed.hostname or "localhost"
        ollama_port = parsed.port or 11434
    elif ollama_host_env.startswith("https://"):
        from urllib.parse import urlparse
        parsed = urlparse(ollama_host_env)
        ollama_host = parsed.hostname or "localhost"
        ollama_port = parsed.port or 11434
    else:
        # Just a hostname
        ollama_host = ollama_host_env
        ollama_port = int(os.getenv("OLLAMA_PORT", "11434"))
    
    config = ChatConfig(
        ollama_host=ollama_host,
        ollama_port=ollama_port,
        ollama_model=os.getenv("OLLAMA_MODEL", "deepseek-r1:8b"),
        websocket_port=int(os.getenv("WEBSOCKET_PORT", "8765")),
        auto_start_server=os.getenv("AUTO_START_SERVER", "true").lower() == "true"
    )
    
    # Create chat interface
    chat = HomelabChatInterface(config)
    
    try:
        # Check and setup dependencies
        ready = await chat.setup_ollama_if_needed()
        
        if ready:
            # Start MCP server
            await chat.start_mcp_server()
            
            # Start interactive chat
            await chat.interactive_chat()
        else:
            chat.print("Please set up the required dependencies and try again.", "yellow")
            
    except Exception as e:
        chat.print(f"Fatal error: {str(e)}", "red")
        return 1
    finally:
        # Cleanup
        if chat.server_task and not chat.server_task.done():
            chat.server_task.cancel()
            try:
                await chat.server_task
            except asyncio.CancelledError:
                pass
                
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))