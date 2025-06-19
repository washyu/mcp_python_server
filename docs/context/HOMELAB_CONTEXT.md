# Homelab Context System

## Overview

The Homelab Context System provides AI agents with intelligent topology awareness to prevent deployment mistakes and enable smarter infrastructure decisions.

## Key Features

### 🏠 Device Role Management
- **development** - Dev machines (excluded from deployments)
- **infrastructure_host** - Core servers (Proxmox, Docker hosts)
- **service_host** - Service deployment targets (Pi devices, VMs)
- **network_device** - Routers, switches, access points
- **storage_device** - NAS, SAN, backup devices

### 🔍 Smart Discovery
- Network scanning to find devices
- Automatic device classification
- Hardware capability detection
- Service dependency mapping

### ✅ Deployment Validation
- Prevents deployment to excluded devices (like dev laptops)
- Validates resource requirements before VM creation
- Suggests optimal placement based on capabilities
- Tracks service relationships

## Available Tools

### Setup & Discovery
- `setup-homelab-wizard` - Interactive setup wizard
- `discover-homelab-topology` - Network discovery and refresh
- `check-homelab-context-staleness` - Check if refresh needed

### Device Management
- `add-homelab-device` - Add device with role and capabilities
- `list-homelab-devices` - View topology with filtering
- `update-device-role` - Change device role/settings
- `get-deployable-hosts` - Find suitable deployment targets

### Service Validation
- `validate-device-for-service` - Check if device can host service
- `get-deployable-hosts` - Filter by resource requirements

## Example Usage

```bash
# Initial setup
setup-homelab-wizard

# Add your development laptop (excluded from deployments)
add-homelab-device ip_address="192.168.10.102" hostname="dev-laptop" role="development" device_type="laptop" exclude_from_homelab=true cpu_cores=8 memory_gb=16 storage_gb=500 notes="Development machine - do not deploy here"

# Add a Pi device for services
add-homelab-device ip_address="192.168.10.50" hostname="pi4-services" role="service_host" device_type="raspberry_pi" cpu_cores=4 memory_gb=8 storage_gb=64 notes="Pi 4 for lightweight services"

# Validate before deploying a service
validate-device-for-service ip_address="192.168.10.50" service_name="pihole" cpu_cores=1 memory_gb=1 storage_gb=8

# Find suitable hosts for a service
get-deployable-hosts min_cpu_cores=2 min_memory_gb=4 min_storage_gb=20
```

## Integration with VM Creation

The system automatically:
1. **Validates** deployment targets before VM creation
2. **Prevents** deployment to excluded devices
3. **Updates** topology context when VMs are created
4. **Tracks** VM capabilities and services

## Storage

Context is stored in `/inventory/homelab-topology.json` with:
- Device inventory with capabilities
- Role-based deployment rules
- Network topology information
- Service dependency tracking
- Automatic staleness detection (10-hour default)

## Benefits

### For Users
- **No more accidents** - Won't try to deploy to your laptop
- **Smart suggestions** - AI knows which Pi can handle which services
- **Resource awareness** - Prevents over-allocation
- **Context preservation** - Maintains understanding across sessions

### For AI Agents
- **Topology awareness** - Understands infrastructure layout
- **Capability matching** - Matches services to suitable hardware
- **Validation logic** - Built-in deployment constraints
- **State tracking** - Maintains consistent infrastructure state

## Example Scenarios

### Scenario 1: Prevent Laptop Deployment
```
User: "Install Jenkins on my development environment"
AI: Checks homelab context → Sees laptop is excluded → Suggests proper server instead
```

### Scenario 2: Pi Device Assessment
```
User: "I have a Pi 4 with 4GB RAM, can it run Nextcloud?"
AI: Validates requirements → Pi has 4GB but Nextcloud needs 8GB → Suggests upgrade or alternative
```

### Scenario 3: Smart VM Placement
```
User: "Create a new VM for AI workloads"
AI: Checks topology → Finds node with GPU → Places VM optimally → Updates context
```

This system ensures AI agents make intelligent infrastructure decisions while preventing common deployment mistakes.