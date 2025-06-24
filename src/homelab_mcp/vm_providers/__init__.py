"""VM Provider package for platform-specific VM operations."""

from .base import VMProvider
from .docker_provider import DockerVMProvider  
from .lxd_provider import LXDVMProvider
from .proxmox_provider import ProxmoxVMProvider

# Registry of available providers
VM_PROVIDERS = {
    "docker": DockerVMProvider,
    "lxd": LXDVMProvider, 
    "proxmox": ProxmoxVMProvider
}

def get_vm_provider(platform: str) -> VMProvider:
    """Factory function to get VM provider for a platform."""
    if platform not in VM_PROVIDERS:
        raise ValueError(f"Unsupported platform: {platform}")
    
    return VM_PROVIDERS[platform]()

__all__ = [
    "VMProvider", 
    "DockerVMProvider", 
    "LXDVMProvider", 
    "ProxmoxVMProvider",
    "VM_PROVIDERS",
    "get_vm_provider"
]