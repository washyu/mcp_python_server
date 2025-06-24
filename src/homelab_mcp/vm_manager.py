"""VM Management module for platform-agnostic VM deployment and management."""

import asyncio
import asyncssh
import json
from typing import Dict, List, Optional, Any
from .sitemap import NetworkSiteMap
from .ssh_tools import ssh_discover_system
from .vm_providers import get_vm_provider


async def deploy_vm_on_platform(
    platform: str,
    vm_name: str,
    target_host: str,
    ssh_user: str,
    ssh_password: str,
    vm_config: Optional[Dict[str, Any]] = None
) -> str:
    """Deploy a VM/container on the specified platform."""
    
    if vm_config is None:
        vm_config = {}
    
    try:
        provider = get_vm_provider(platform)
        
        async with asyncssh.connect(
            target_host,
            username=ssh_user,
            password=ssh_password,
            known_hosts=None
        ) as conn:
            
            result = await provider.deploy_vm(conn, vm_name, vm_config)
            
            # Auto-discover and catalog the new VM
            if result.get("status") == "success" and result.get("ip"):
                await _auto_discover_vm(result, target_host)
            
            return json.dumps(result, indent=2)
            
    except ValueError as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Deployment failed: {str(e)}"
        })


async def delete_vm_on_platform(
    platform: str,
    vm_name: str,
    target_host: str,
    ssh_user: str,
    ssh_password: str
) -> str:
    """Delete a VM/container on the specified platform."""
    
    try:
        provider = get_vm_provider(platform)
        
        async with asyncssh.connect(
            target_host,
            username=ssh_user,
            password=ssh_password,
            known_hosts=None
        ) as conn:
            
            result = await provider.delete_vm(conn, vm_name)
            return json.dumps(result, indent=2)
            
    except ValueError as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Deletion failed: {str(e)}"
        })


async def list_vms_on_host(
    target_host: str,
    ssh_user: str,
    ssh_password: str,
    platforms: List[str]
) -> str:
    """List all VMs/containers on the target host across specified platforms."""
    
    try:
        async with asyncssh.connect(
            target_host,
            username=ssh_user,
            password=ssh_password,
            known_hosts=None
        ) as conn:
            
            all_vms = []
            
            for platform in platforms:
                try:
                    provider = get_vm_provider(platform)
                    vms = await provider.list_vms(conn)
                    all_vms.extend(vms)
                except ValueError:
                    # Skip unsupported platforms
                    continue
                except Exception:
                    # Skip platforms that fail to list
                    continue
            
            return json.dumps({
                "status": "success",
                "host": target_host,
                "total_vms": len(all_vms),
                "vms": all_vms
            }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Listing failed: {str(e)}"
        })


# Auto-discovery integration
async def _auto_discover_vm(vm_info: Dict[str, Any], target_host: str) -> Optional[int]:
    """Automatically discover and catalog a newly created VM."""
    
    if not vm_info.get('ip'):
        return None
    
    try:
        sitemap = NetworkSiteMap()
        
        discovery_result = await ssh_discover_system(
            hostname=vm_info['ip'],
            username="homelab",
            password="homelab123",
            port=vm_info.get('port', 22)
        )
        
        discovery_data = json.loads(discovery_result)
        
        if discovery_data["status"] == "success":
            # Store in sitemap
            device = sitemap.parse_discovery_output(discovery_result)
            device_id = sitemap.store_device(device)
            sitemap.store_discovery_history(device_id, discovery_result)
            return device_id
        
    except Exception:
        # Silent failure for auto-discovery
        pass
    
    return None