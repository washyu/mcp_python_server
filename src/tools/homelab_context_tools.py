"""
Homelab Context Tools - MCP tools for managing homelab topology and device roles
"""

from typing import List, Dict, Any, Optional
from mcp.types import TextContent, Tool

from ..utils.homelab_context import (
    HomelabContextManager, 
    HomelabDevice, 
    DeviceCapabilities
)


# Tool definitions
HOMELAB_CONTEXT_TOOLS = [
    Tool(
        name="setup-homelab-wizard",
        description="Interactive wizard to set up homelab topology and device roles",
        inputSchema={
            "type": "object",
            "properties": {
                "skip_discovery": {
                    "type": "boolean",
                    "description": "Skip automatic network discovery",
                    "default": False
                },
                "network_range": {
                    "type": "string",
                    "description": "Network range to scan (e.g., 192.168.10.0/24)",
                    "default": "192.168.10.0/24"
                }
            },
            "required": []
        }
    ),
    Tool(
        name="discover-homelab-topology",
        description="Network scan to find devices (basic discovery only - for hardware details use discover_remote_system with IP address)",
        inputSchema={
            "type": "object",
            "properties": {
                "network_range": {
                    "type": "string",
                    "description": "Network range to scan (e.g., 192.168.10.0/24)"
                },
                "force_refresh": {
                    "type": "boolean",
                    "description": "Force refresh even if context is not stale",
                    "default": False
                }
            },
            "required": []
        }
    ),
    Tool(
        name="add-homelab-device",
        description="Add a device to the homelab topology with specific role and capabilities",
        inputSchema={
            "type": "object",
            "properties": {
                "ip_address": {
                    "type": "string",
                    "description": "IP address of the device"
                },
                "hostname": {
                    "type": "string",
                    "description": "Hostname of the device"
                },
                "role": {
                    "type": "string",
                    "description": "Device role",
                    "enum": ["development", "infrastructure_host", "service_host", "network_device", "storage_device"]
                },
                "device_type": {
                    "type": "string",
                    "description": "Type of device (e.g., laptop, pi, server, vm, container)"
                },
                "exclude_from_homelab": {
                    "type": "boolean",
                    "description": "Exclude this device from homelab service deployments",
                    "default": False
                },
                "cpu_cores": {
                    "type": "integer",
                    "description": "Number of CPU cores",
                    "default": 0
                },
                "memory_gb": {
                    "type": "integer",
                    "description": "Memory in GB",
                    "default": 0
                },
                "storage_gb": {
                    "type": "integer",
                    "description": "Storage in GB",
                    "default": 0
                },
                "notes": {
                    "type": "string",
                    "description": "Additional notes about the device",
                    "default": ""
                }
            },
            "required": ["ip_address", "hostname", "role", "device_type"]
        }
    ),
    Tool(
        name="list-homelab-devices",
        description="List all devices in the homelab topology with their roles and capabilities",
        inputSchema={
            "type": "object",
            "properties": {
                "role_filter": {
                    "type": "string",
                    "description": "Filter devices by role",
                    "enum": ["development", "infrastructure_host", "service_host", "network_device", "storage_device"]
                },
                "deployable_only": {
                    "type": "boolean",
                    "description": "Show only devices that can have services deployed",
                    "default": False
                },
                "include_excluded": {
                    "type": "boolean",
                    "description": "Include devices excluded from homelab",
                    "default": True
                }
            },
            "required": []
        }
    ),
    Tool(
        name="validate-device-for-service",
        description="Check if a device can host a specific service based on requirements",
        inputSchema={
            "type": "object",
            "properties": {
                "ip_address": {
                    "type": "string",
                    "description": "IP address of the device to validate"
                },
                "service_name": {
                    "type": "string",
                    "description": "Name of the service to validate for"
                },
                "cpu_cores": {
                    "type": "integer",
                    "description": "Required CPU cores",
                    "default": 1
                },
                "memory_gb": {
                    "type": "integer",
                    "description": "Required memory in GB",
                    "default": 1
                },
                "storage_gb": {
                    "type": "integer",
                    "description": "Required storage in GB",
                    "default": 10
                },
                "requires_gpu": {
                    "type": "boolean",
                    "description": "Service requires GPU",
                    "default": False
                }
            },
            "required": ["ip_address", "service_name"]
        }
    ),
    Tool(
        name="update-device-role",
        description="Update the role of a device in the homelab topology",
        inputSchema={
            "type": "object",
            "properties": {
                "ip_address": {
                    "type": "string",
                    "description": "IP address of the device"
                },
                "new_role": {
                    "type": "string",
                    "description": "New role for the device",
                    "enum": ["development", "infrastructure_host", "service_host", "network_device", "storage_device"]
                },
                "exclude_from_homelab": {
                    "type": "boolean",
                    "description": "Whether to exclude from homelab deployments"
                },
                "notes": {
                    "type": "string",
                    "description": "Updated notes for the device"
                }
            },
            "required": ["ip_address", "new_role"]
        }
    ),
    Tool(
        name="get-deployable-hosts",
        description="Get list of hosts that can be used for service deployment",
        inputSchema={
            "type": "object",
            "properties": {
                "min_cpu_cores": {
                    "type": "integer",
                    "description": "Minimum CPU cores required",
                    "default": 1
                },
                "min_memory_gb": {
                    "type": "integer",
                    "description": "Minimum memory in GB required",
                    "default": 1
                },
                "min_storage_gb": {
                    "type": "integer",
                    "description": "Minimum storage in GB required",
                    "default": 10
                },
                "requires_gpu": {
                    "type": "boolean",
                    "description": "Filter for hosts with GPU",
                    "default": False
                }
            },
            "required": []
        }
    ),
    Tool(
        name="check-homelab-context-staleness",
        description="Check if homelab context needs to be refreshed",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )
]


async def handle_homelab_context_tool(tool_name: str, kwargs: dict) -> List[TextContent]:
    """Handle homelab context tool requests"""
    context_manager = HomelabContextManager()
    
    try:
        if tool_name == "setup-homelab-wizard":
            return await _setup_homelab_wizard(context_manager, kwargs)
        
        elif tool_name == "discover-homelab-topology":
            return await _discover_homelab_topology(context_manager, kwargs)
        
        elif tool_name == "add-homelab-device":
            return await _add_homelab_device(context_manager, kwargs)
        
        elif tool_name == "list-homelab-devices":
            return await _list_homelab_devices(context_manager, kwargs)
        
        elif tool_name == "validate-device-for-service":
            return await _validate_device_for_service(context_manager, kwargs)
        
        elif tool_name == "update-device-role":
            return await _update_device_role(context_manager, kwargs)
        
        elif tool_name == "get-deployable-hosts":
            return await _get_deployable_hosts(context_manager, kwargs)
        
        elif tool_name == "check-homelab-context-staleness":
            return await _check_homelab_context_staleness(context_manager, kwargs)
        
        else:
            return [TextContent(
                type="text",
                text=f"❌ Unknown homelab context tool: {tool_name}"
            )]
            
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"❌ Error executing {tool_name}: {str(e)}"
        )]


async def _setup_homelab_wizard(context_manager: HomelabContextManager, kwargs: dict) -> List[TextContent]:
    """Run the homelab setup wizard"""
    skip_discovery = kwargs.get("skip_discovery", False)
    network_range = kwargs.get("network_range", "192.168.10.0/24")
    
    result = []
    result.append(TextContent(
        type="text",
        text="🏠 **Homelab Setup Wizard**\\n\\n"
             "This wizard will help set up your homelab topology and device roles.\\n"
    ))
    
    # Check if we should run discovery
    if not skip_discovery:
        result.append(TextContent(
            type="text",
            text=f"🔍 **Step 1: Network Discovery**\\n"
                 f"Scanning network range: {network_range}\\n"
        ))
        
        discovered_ips = await context_manager.discover_network_devices(network_range)
        
        result.append(TextContent(
            type="text",
            text=f"✅ Discovered {len(discovered_ips)} devices: {', '.join(discovered_ips)}\\n\\n"
        ))
        
        # Show current topology
        topology = await context_manager.load_topology()
        known_devices = list(topology["devices"].keys())
        
        result.append(TextContent(
            type="text",
            text=f"📋 **Current Topology**: {len(known_devices)} known devices\\n\\n"
        ))
        
        # Suggest new devices to add
        new_devices = [ip for ip in discovered_ips if ip not in known_devices]
        if new_devices:
            result.append(TextContent(
                type="text",
                text=f"🆕 **New devices found**: {', '.join(new_devices)}\\n\\n"
                     "Use `add-homelab-device` to configure each new device with its role and capabilities.\\n\\n"
            ))
    
    # Show device role explanations
    result.append(TextContent(
        type="text",
        text="📝 **Device Roles:**\\n"
             "• **development** - Dev machines (excluded from deployments)\\n"
             "• **infrastructure_host** - Core servers (Proxmox, Docker hosts)\\n"
             "• **service_host** - Service deployment targets (Pi devices, VMs)\\n"
             "• **network_device** - Routers, switches, access points\\n"
             "• **storage_device** - NAS, SAN, backup devices\\n\\n"
    ))
    
    result.append(TextContent(
        type="text",
        text="✅ **Wizard Complete**\\n\\n"
             "Next steps:\\n"
             "1. Use `add-homelab-device` to configure discovered devices\\n"
             "2. Use `list-homelab-devices` to view your topology\\n"
             "3. Use `validate-device-for-service` before deploying services\\n"
    ))
    
    return result


async def _discover_homelab_topology(context_manager: HomelabContextManager, kwargs: dict) -> List[TextContent]:
    """Discover homelab topology"""
    force_refresh = kwargs.get("force_refresh", False)
    network_range = kwargs.get("network_range")
    
    # Check if user is trying to get hardware info for a specific IP
    if "-ip" in str(kwargs) or any(key in kwargs for key in ["ip", "ipaddress", "ip_address"]):
        ip_value = kwargs.get("ip") or kwargs.get("ipaddress") or kwargs.get("ip_address") or "unknown"
        return [TextContent(
            type="text",
            text=f"⚠️ **Wrong tool for hardware discovery!**\n\n"
                 f"You're trying to get hardware details for a specific IP ({ip_value}).\n\n"
                 f"**Use this instead:**\n"
                 f"`discover_remote_system ip_address=\"{ip_value}\"`\n\n"
                 f"This will give you actual hardware specs (CPU, memory, storage, etc.)\n\n"
                 f"Note: discover-homelab-topology only does network scanning, not hardware discovery."
        )]
    
    # Check if refresh is needed
    if not force_refresh:
        is_stale = await context_manager.is_context_stale()
        if not is_stale:
            return [TextContent(
                type="text",
                text="ℹ️ Homelab context is up to date. Use `force_refresh=true` to refresh anyway."
            )]
    
    stats = await context_manager.refresh_topology()
    
    result_text = f"🔍 **Homelab Topology Discovery Complete**\\n\\n"
    result_text += f"📊 **Stats:**\\n"
    result_text += f"• Discovered devices: {stats['discovered_devices']}\\n"
    result_text += f"• New devices: {stats['new_devices']}\\n"
    result_text += f"• Updated devices: {stats['updated_devices']}\\n"
    
    if stats['errors']:
        result_text += f"\\n⚠️ **Errors:**\\n"
        for error in stats['errors']:
            result_text += f"• {error}\\n"
    
    result_text += f"\\n✅ Homelab context refreshed successfully."
    result_text += f"\\n\\n💡 **Tip:** To get hardware details for a specific device, use:"
    result_text += f"\\n`discover_remote_system ip_address=\"<IP>\"`"
    
    return [TextContent(type="text", text=result_text)]


async def _add_homelab_device(context_manager: HomelabContextManager, kwargs: dict) -> List[TextContent]:
    """Add a device to homelab topology"""
    # Extract device info
    ip_address = kwargs["ip_address"]
    hostname = kwargs["hostname"]
    role = kwargs["role"]
    device_type = kwargs["device_type"]
    exclude_from_homelab = kwargs.get("exclude_from_homelab", False)
    
    # Extract capabilities
    capabilities = DeviceCapabilities(
        cpu_cores=kwargs.get("cpu_cores", 0),
        memory_gb=kwargs.get("memory_gb", 0),
        storage_gb=kwargs.get("storage_gb", 0),
        network_interfaces=[]
    )
    
    # Create device
    device = HomelabDevice(
        ip_address=ip_address,
        hostname=hostname,
        role=role,
        device_type=device_type,
        exclude_from_homelab=exclude_from_homelab,
        capabilities=capabilities,
        services=[],
        notes=kwargs.get("notes", "")
    )
    
    # Add to topology
    success = await context_manager.add_device(device)
    
    if success:
        deploy_status = "❌ Excluded from deployments" if exclude_from_homelab else "✅ Available for deployments"
        
        result_text = f"✅ **Device Added Successfully**\\n\\n"
        result_text += f"**Device:** {hostname} ({ip_address})\\n"
        result_text += f"**Role:** {role}\\n"
        result_text += f"**Type:** {device_type}\\n"
        result_text += f"**Deployment Status:** {deploy_status}\\n"
        result_text += f"**Resources:** {capabilities.cpu_cores} cores, {capabilities.memory_gb}GB RAM, {capabilities.storage_gb}GB storage\\n"
        
        if device.notes:
            result_text += f"**Notes:** {device.notes}\\n"
        
        return [TextContent(type="text", text=result_text)]
    else:
        return [TextContent(
            type="text",
            text=f"❌ Failed to add device {hostname} ({ip_address})"
        )]


async def _list_homelab_devices(context_manager: HomelabContextManager, kwargs: dict) -> List[TextContent]:
    """List homelab devices"""
    topology = await context_manager.load_topology()
    devices = topology["devices"]
    
    role_filter = kwargs.get("role_filter")
    deployable_only = kwargs.get("deployable_only", False)
    include_excluded = kwargs.get("include_excluded", True)
    
    # Filter devices
    filtered_devices = {}
    for ip, device_data in devices.items():
        # Role filter
        if role_filter and device_data.get("role") != role_filter:
            continue
            
        # Deployable filter
        if deployable_only:
            if device_data.get("exclude_from_homelab", False):
                continue
            role_config = topology["device_roles"].get(device_data.get("role"), {})
            if not role_config.get("allow_service_deployment", False):
                continue
        
        # Excluded filter
        if not include_excluded and device_data.get("exclude_from_homelab", False):
            continue
            
        filtered_devices[ip] = device_data
    
    if not filtered_devices:
        return [TextContent(
            type="text",
            text="📱 No devices found matching the specified criteria."
        )]
    
    result_text = f"🏠 **Homelab Devices** ({len(filtered_devices)} devices)\\n\\n"
    
    # Group by role
    roles = {}
    for ip, device_data in filtered_devices.items():
        role = device_data.get("role", "unknown")
        if role not in roles:
            roles[role] = []
        roles[role].append((ip, device_data))
    
    for role, device_list in roles.items():
        role_config = topology["device_roles"].get(role, {})
        result_text += f"## 📋 {role.replace('_', ' ').title()}\\n"
        result_text += f"*{role_config.get('description', 'No description')}*\\n\\n"
        
        for ip, device_data in device_list:
            hostname = device_data.get("hostname", "unknown")
            device_type = device_data.get("device_type", "unknown")
            excluded = device_data.get("exclude_from_homelab", False)
            capabilities = device_data.get("capabilities", {})
            
            status_icon = "❌" if excluded else "✅"
            result_text += f"**{status_icon} {hostname}** ({ip})\\n"
            result_text += f"  Type: {device_type}\\n"
            
            if capabilities.get("cpu_cores", 0) > 0:
                result_text += f"  Resources: {capabilities['cpu_cores']} cores, {capabilities['memory_gb']}GB RAM, {capabilities['storage_gb']}GB storage\\n"
            else:
                result_text += f"  Resources: Unknown\\n"
            
            if device_data.get("notes"):
                result_text += f"  Notes: {device_data['notes']}\\n"
            
            result_text += f"\\n"
        
        result_text += f"\\n"
    
    return [TextContent(type="text", text=result_text)]


async def _validate_device_for_service(context_manager: HomelabContextManager, kwargs: dict) -> List[TextContent]:
    """Validate device for service deployment"""
    ip_address = kwargs["ip_address"]
    service_name = kwargs["service_name"]
    
    # Build service requirements
    requirements = {
        "cpu_cores": kwargs.get("cpu_cores", 1),
        "memory_gb": kwargs.get("memory_gb", 1),
        "storage_gb": kwargs.get("storage_gb", 10),
        "requires_gpu": kwargs.get("requires_gpu", False)
    }
    
    validation = await context_manager.validate_device_for_service(ip_address, requirements)
    
    device = await context_manager.get_device(ip_address)
    device_name = device.hostname if device else ip_address
    
    if validation["valid"]:
        result_text = f"✅ **Device Validation: PASSED**\\n\\n"
        result_text += f"**Device:** {device_name} ({ip_address})\\n"
        result_text += f"**Service:** {service_name}\\n"
        result_text += f"**Status:** {validation['reason']}\\n\\n"
        result_text += f"**Requirements Met:**\\n"
        result_text += f"• CPU: {requirements['cpu_cores']} cores ✅\\n"
        result_text += f"• Memory: {requirements['memory_gb']} GB ✅\\n"
        result_text += f"• Storage: {requirements['storage_gb']} GB ✅\\n"
        
        if requirements['requires_gpu']:
            gpu_available = device and device.capabilities.gpu is not None
            gpu_status = "✅" if gpu_available else "❌"
            result_text += f"• GPU: Required {gpu_status}\\n"
    
    else:
        result_text = f"❌ **Device Validation: FAILED**\\n\\n"
        result_text += f"**Device:** {device_name} ({ip_address})\\n"
        result_text += f"**Service:** {service_name}\\n"
        result_text += f"**Reason:** {validation['reason']}\\n\\n"
        
        if device:
            result_text += f"**Device Capabilities:**\\n"
            result_text += f"• CPU: {device.capabilities.cpu_cores} cores\\n"
            result_text += f"• Memory: {device.capabilities.memory_gb} GB\\n"
            result_text += f"• Storage: {device.capabilities.storage_gb} GB\\n"
            result_text += f"• Role: {device.role}\\n"
            result_text += f"• Excluded: {device.exclude_from_homelab}\\n"
    
    return [TextContent(type="text", text=result_text)]


async def _update_device_role(context_manager: HomelabContextManager, kwargs: dict) -> List[TextContent]:
    """Update device role"""
    ip_address = kwargs["ip_address"]
    new_role = kwargs["new_role"]
    exclude_from_homelab = kwargs.get("exclude_from_homelab")
    notes = kwargs.get("notes")
    
    # Get existing device
    device = await context_manager.get_device(ip_address)
    if not device:
        return [TextContent(
            type="text",
            text=f"❌ Device {ip_address} not found in homelab topology"
        )]
    
    # Update device
    old_role = device.role
    device.role = new_role
    
    if exclude_from_homelab is not None:
        device.exclude_from_homelab = exclude_from_homelab
    
    if notes is not None:
        device.notes = notes
    
    # Save changes
    success = await context_manager.add_device(device)
    
    if success:
        result_text = f"✅ **Device Updated Successfully**\\n\\n"
        result_text += f"**Device:** {device.hostname} ({ip_address})\\n"
        result_text += f"**Role:** {old_role} → {new_role}\\n"
        
        if exclude_from_homelab is not None:
            status = "Excluded from" if exclude_from_homelab else "Available for"
            result_text += f"**Deployment:** {status} homelab deployments\\n"
        
        if notes:
            result_text += f"**Notes:** {notes}\\n"
        
        return [TextContent(type="text", text=result_text)]
    else:
        return [TextContent(
            type="text",
            text=f"❌ Failed to update device {device.hostname} ({ip_address})"
        )]


async def _get_deployable_hosts(context_manager: HomelabContextManager, kwargs: dict) -> List[TextContent]:
    """Get deployable hosts"""
    min_cpu = kwargs.get("min_cpu_cores", 1)
    min_memory = kwargs.get("min_memory_gb", 1)
    min_storage = kwargs.get("min_storage_gb", 10)
    requires_gpu = kwargs.get("requires_gpu", False)
    
    deployable_devices = await context_manager.get_deployable_devices()
    
    # Filter by requirements
    suitable_devices = []
    for device in deployable_devices:
        if (device.capabilities.cpu_cores >= min_cpu and
            device.capabilities.memory_gb >= min_memory and
            device.capabilities.storage_gb >= min_storage):
            
            if requires_gpu and not device.capabilities.gpu:
                continue
                
            suitable_devices.append(device)
    
    if not suitable_devices:
        result_text = f"❌ **No Suitable Hosts Found**\\n\\n"
        result_text += f"**Requirements:**\\n"
        result_text += f"• CPU: {min_cpu}+ cores\\n"
        result_text += f"• Memory: {min_memory}+ GB\\n"
        result_text += f"• Storage: {min_storage}+ GB\\n"
        result_text += f"• GPU: {'Required' if requires_gpu else 'Not required'}\\n\\n"
        result_text += f"Consider updating device capabilities or adjusting requirements."
        
        return [TextContent(type="text", text=result_text)]
    
    result_text = f"🎯 **Deployable Hosts** ({len(suitable_devices)} available)\\n\\n"
    result_text += f"**Requirements:** {min_cpu}+ cores, {min_memory}+ GB RAM, {min_storage}+ GB storage"
    if requires_gpu:
        result_text += f", GPU required"
    result_text += f"\\n\\n"
    
    for device in suitable_devices:
        result_text += f"✅ **{device.hostname}** ({device.ip_address})\\n"
        result_text += f"  Role: {device.role}\\n"
        result_text += f"  Resources: {device.capabilities.cpu_cores} cores, {device.capabilities.memory_gb}GB RAM, {device.capabilities.storage_gb}GB storage\\n"
        
        if device.capabilities.gpu:
            result_text += f"  GPU: {device.capabilities.gpu.get('type', 'Unknown')} {device.capabilities.gpu.get('model', '')}\\n"
        
        if device.notes:
            result_text += f"  Notes: {device.notes}\\n"
        
        result_text += f"\\n"
    
    return [TextContent(type="text", text=result_text)]


async def _check_homelab_context_staleness(context_manager: HomelabContextManager, kwargs: dict) -> List[TextContent]:
    """Check homelab context staleness"""
    is_stale = await context_manager.is_context_stale()
    topology = await context_manager.load_topology()
    
    last_updated = topology["topology"].get("last_updated", "Never")
    staleness_hours = topology["topology"]["discovery_settings"]["staleness_hours"]
    
    if is_stale:
        result_text = f"⚠️ **Homelab Context is Stale**\\n\\n"
        result_text += f"**Last Updated:** {last_updated}\\n"
        result_text += f"**Staleness Threshold:** {staleness_hours} hours\\n\\n"
        result_text += f"Recommendation: Run `discover-homelab-topology` to refresh context."
    else:
        result_text = f"✅ **Homelab Context is Current**\\n\\n"
        result_text += f"**Last Updated:** {last_updated}\\n"
        result_text += f"**Staleness Threshold:** {staleness_hours} hours\\n\\n"
        result_text += f"Context is up to date."
    
    return [TextContent(type="text", text=result_text)]