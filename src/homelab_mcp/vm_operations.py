"""VM Operations module using the new provider architecture."""

import asyncio
import asyncssh
import json
from typing import Dict, List, Optional, Any

from .vm_providers import get_vm_provider


async def control_vm_state(
    platform: str,
    vm_name: str,
    action: str,
    target_host: str,
    ssh_user: str,
    ssh_password: str
) -> str:
    """Control VM/container state (start, stop, restart)."""
    
    try:
        provider = get_vm_provider(platform)
        
        async with asyncssh.connect(
            target_host,
            username=ssh_user,
            password=ssh_password,
            known_hosts=None
        ) as conn:
            
            result = await provider.control_vm(conn, vm_name, action)
            return json.dumps(result, indent=2)
            
    except ValueError as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"VM control failed: {str(e)}"
        })


async def get_vm_detailed_status(
    platform: str,
    vm_name: str,
    target_host: str,
    ssh_user: str,
    ssh_password: str
) -> str:
    """Get detailed status and resource usage for a VM/container."""
    
    try:
        provider = get_vm_provider(platform)
        
        async with asyncssh.connect(
            target_host,
            username=ssh_user,
            password=ssh_password,
            known_hosts=None
        ) as conn:
            
            result = await provider.get_vm_status(conn, vm_name)
            return json.dumps(result, indent=2)
            
    except ValueError as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Status check failed: {str(e)}"
        })


async def get_vm_logs(
    platform: str,
    vm_name: str,
    target_host: str,
    ssh_user: str,
    ssh_password: str,
    lines: int = 50,
    follow: bool = False
) -> str:
    """Get logs from a VM/container."""
    
    try:
        provider = get_vm_provider(platform)
        
        async with asyncssh.connect(
            target_host,
            username=ssh_user,
            password=ssh_password,
            known_hosts=None
        ) as conn:
            
            result = await provider.get_vm_logs(conn, vm_name, lines, follow)
            return json.dumps(result, indent=2)
            
    except ValueError as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Log retrieval failed: {str(e)}"
        })


async def manage_vm_services(
    platform: str,
    vm_name: str,
    action: str,
    target_host: str,
    ssh_user: str,
    ssh_password: str,
    service_name: Optional[str] = None
) -> str:
    """Manage services inside a VM/container."""
    
    try:
        provider = get_vm_provider(platform)
        
        async with asyncssh.connect(
            target_host,
            username=ssh_user,
            password=ssh_password,
            known_hosts=None
        ) as conn:
            
            result = await provider.manage_vm_services(conn, vm_name, action, service_name)
            return json.dumps(result, indent=2)
            
    except ValueError as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Service management failed: {str(e)}"
        })