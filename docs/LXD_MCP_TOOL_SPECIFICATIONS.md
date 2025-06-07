# LXD MCP Tool Specifications

## Overview
This document defines the MCP (Model Context Protocol) tool specifications for LXD integration. These tools provide AI agents with comprehensive LXD container management capabilities alongside existing Proxmox functionality.

## Tool Categories

### 1. LXD Setup & Discovery Tools

#### `setup_lxd_host`
**Description**: Install and configure LXD on a target host (Raspberry Pi or x86_64 server)

**Parameters**:
```json
{
  "host": {
    "type": "string",
    "description": "Target host IP address or hostname",
    "required": true
  },
  "ssh_user": {
    "type": "string", 
    "description": "SSH username for connection",
    "default": "ubuntu"
  },
  "ssh_key_path": {
    "type": "string",
    "description": "Path to SSH private key",
    "default": "~/.ssh/id_rsa"
  },
  "installation_method": {
    "type": "string",
    "enum": ["snap", "apt", "auto"],
    "description": "Installation method (auto-detects best option)",
    "default": "auto"
  },
  "storage_backend": {
    "type": "string",
    "enum": ["dir", "zfs", "btrfs"],
    "description": "Storage backend for LXD",
    "default": "dir"
  },
  "cluster_join": {
    "type": "boolean",
    "description": "Join existing LXD cluster",
    "default": false
  },
  "cluster_address": {
    "type": "string",
    "description": "Existing cluster address to join (if cluster_join=true)"
  }
}
```

**Returns**:
```json
{
  "success": true,
  "host": "192.168.10.101",
  "lxd_version": "5.0.2",
  "installation_method": "snap",
  "storage_backend": "dir",
  "cluster_member": false,
  "api_endpoint": "https://192.168.10.101:8443",
  "setup_time_seconds": 120,
  "message": "LXD successfully installed and configured"
}
```

#### `discover_lxd_hosts`
**Description**: Discover existing LXD installations on the network

**Parameters**:
```json
{
  "network_range": {
    "type": "string",
    "description": "Network range to scan (CIDR notation)",
    "default": "192.168.10.0/24"
  },
  "ssh_users": {
    "type": "array",
    "items": {"type": "string"},
    "description": "SSH usernames to try",
    "default": ["ubuntu", "pi", "admin"]
  },
  "timeout_seconds": {
    "type": "integer",
    "description": "Connection timeout per host",
    "default": 5
  }
}
```

**Returns**:
```json
{
  "hosts_found": [
    {
      "host": "192.168.10.101",
      "ssh_user": "ubuntu", 
      "lxd_installed": true,
      "lxd_version": "5.0.2",
      "cluster_member": true,
      "cluster_name": "pi-cluster",
      "api_accessible": true
    },
    {
      "host": "192.168.10.102",
      "ssh_user": "ubuntu",
      "lxd_installed": false,
      "os_info": "Ubuntu 22.04 LTS"
    }
  ],
  "scan_time_seconds": 45,
  "total_hosts_scanned": 254
}
```

#### `test_lxd_connection`
**Description**: Test connectivity and authentication to LXD host

**Parameters**:
```json
{
  "host": {
    "type": "string", 
    "description": "LXD host address",
    "required": true
  },
  "connection_method": {
    "type": "string",
    "enum": ["ssh_tunnel", "https", "unix_socket"],
    "description": "Connection method to test",
    "default": "ssh_tunnel"
  }
}
```

### 2. LXD Discovery Tools

#### `lxd_list_hosts`
**Description**: List all configured LXD hosts in inventory

**Parameters**:
```json
{
  "include_offline": {
    "type": "boolean",
    "description": "Include offline hosts in results",
    "default": false
  },
  "cluster_only": {
    "type": "boolean", 
    "description": "Show only cluster members",
    "default": false
  }
}
```

**Returns**:
```json
{
  "hosts": [
    {
      "host": "192.168.10.101",
      "status": "online",
      "lxd_version": "5.0.2", 
      "cluster_member": true,
      "cluster_name": "pi-cluster",
      "containers": 3,
      "cpu_cores": 4,
      "memory_total_gb": 8,
      "memory_used_gb": 2.1,
      "storage_pools": ["default", "ssd-pool"]
    }
  ],
  "total_hosts": 2,
  "online_hosts": 2,
  "cluster_hosts": 2
}
```

#### `lxd_list_containers`
**Description**: List LXD containers with smart filtering

**Parameters**:
```json
{
  "host": {
    "type": "string",
    "description": "Specific host to query (omit for all hosts)"
  },
  "status": {
    "type": "string",
    "enum": ["running", "stopped", "frozen"],
    "description": "Filter by container status"
  },
  "image": {
    "type": "string",
    "description": "Filter by image (e.g., 'ubuntu:22.04')"
  },
  "name_pattern": {
    "type": "string",
    "description": "Filter by name pattern (supports wildcards)"
  },
  "min_memory_mb": {
    "type": "integer",
    "description": "Filter by minimum memory allocation"
  },
  "profile": {
    "type": "string",
    "description": "Filter by profile name"
  }
}
```

**Returns**:
```json
{
  "containers": [
    {
      "name": "web-server",
      "host": "192.168.10.101",
      "status": "running",
      "image": "ubuntu:22.04",
      "architecture": "aarch64",
      "ipv4_addresses": ["10.0.0.10"],
      "cpu_usage_percent": 15.2,
      "memory_usage_mb": 512,
      "memory_limit_mb": 2048,
      "disk_usage_mb": 1024,
      "profiles": ["default", "web-profile"],
      "created_at": "2024-01-30T09:00:00Z",
      "last_used_at": "2024-01-30T10:30:00Z"
    }
  ],
  "total_containers": 5,
  "running_containers": 3,
  "hosts_queried": 2
}
```

#### `lxd_list_images`
**Description**: List available container images

**Parameters**:
```json
{
  "host": {
    "type": "string",
    "description": "Specific host to query"
  },
  "architecture": {
    "type": "string",
    "enum": ["aarch64", "x86_64"],
    "description": "Filter by architecture"
  },
  "distribution": {
    "type": "string",
    "description": "Filter by distribution (ubuntu, alpine, etc.)"
  },
  "include_remote": {
    "type": "boolean",
    "description": "Include remote image repositories",
    "default": false
  }
}
```

#### `lxd_list_networks`
**Description**: List LXD network configurations

**Parameters**:
```json
{
  "host": {
    "type": "string",
    "description": "Specific host to query"
  },
  "network_type": {
    "type": "string",
    "enum": ["bridge", "macvlan", "sriov", "ovn"],
    "description": "Filter by network type"
  }
}
```

#### `lxd_list_storage`
**Description**: List LXD storage pools and usage

**Parameters**:
```json
{
  "host": {
    "type": "string",
    "description": "Specific host to query"
  },
  "driver": {
    "type": "string",
    "enum": ["dir", "zfs", "btrfs", "lvm"],
    "description": "Filter by storage driver"
  },
  "include_usage": {
    "type": "boolean",
    "description": "Include detailed usage statistics",
    "default": true
  }
}
```

### 3. LXD Container Management Tools

#### `lxd_create_container`
**Description**: Create new LXD container with intelligent configuration

**Parameters**:
```json
{
  "name": {
    "type": "string",
    "description": "Container name",
    "required": true
  },
  "host": {
    "type": "string",
    "description": "Target LXD host (auto-selected if omitted)"
  },
  "image": {
    "type": "string", 
    "description": "Container image",
    "default": "ubuntu:22.04"
  },
  "cpu_limit": {
    "type": "string",
    "description": "CPU limit (e.g., '2', '1.5')",
    "default": "1"
  },
  "memory_limit": {
    "type": "string",
    "description": "Memory limit (e.g., '2GB', '512MB')",
    "default": "1GB"
  },
  "disk_limit": {
    "type": "string",
    "description": "Disk limit (e.g., '20GB')",
    "default": "10GB"
  },
  "network": {
    "type": "string",
    "description": "Network to connect to",
    "default": "lxdbr0"
  },
  "profiles": {
    "type": "array",
    "items": {"type": "string"},
    "description": "Profiles to apply",
    "default": ["default"]
  },
  "port_forwards": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "host_port": {"type": "integer"},
        "container_port": {"type": "integer"},
        "protocol": {"type": "string", "enum": ["tcp", "udp"]}
      }
    },
    "description": "Port forwarding rules"
  },
  "auto_start": {
    "type": "boolean", 
    "description": "Start container after creation",
    "default": true
  },
  "privileged": {
    "type": "boolean",
    "description": "Create privileged container",
    "default": false
  }
}
```

**Returns**:
```json
{
  "success": true,
  "name": "web-server",
  "host": "192.168.10.101",
  "status": "running",
  "fingerprint": "abc123def456",
  "ipv4_addresses": ["10.0.0.10"],
  "resource_allocation": {
    "cpu_limit": "2",
    "memory_limit": "2GB", 
    "disk_limit": "20GB"
  },
  "port_forwards": [
    {"host_port": 8080, "container_port": 80, "protocol": "tcp"}
  ],
  "creation_time_seconds": 45,
  "message": "Container 'web-server' created and started successfully"
}
```

#### `lxd_start_container`
**Description**: Start a stopped LXD container

**Parameters**:
```json
{
  "name": {
    "type": "string",
    "description": "Container name",
    "required": true
  },
  "host": {
    "type": "string",
    "description": "LXD host (auto-detected if omitted)"
  },
  "timeout_seconds": {
    "type": "integer",
    "description": "Startup timeout",
    "default": 30
  }
}
```

#### `lxd_stop_container`
**Description**: Stop a running LXD container

**Parameters**:
```json
{
  "name": {
    "type": "string", 
    "description": "Container name",
    "required": true
  },
  "host": {
    "type": "string",
    "description": "LXD host (auto-detected if omitted)"
  },
  "force": {
    "type": "boolean",
    "description": "Force stop (kill) container",
    "default": false
  },
  "timeout_seconds": {
    "type": "integer",
    "description": "Graceful shutdown timeout before force",
    "default": 30
  }
}
```

#### `lxd_restart_container`
**Description**: Restart an LXD container

**Parameters**:
```json
{
  "name": {
    "type": "string",
    "description": "Container name", 
    "required": true
  },
  "host": {
    "type": "string",
    "description": "LXD host (auto-detected if omitted)"
  },
  "force": {
    "type": "boolean",
    "description": "Force restart",
    "default": false
  }
}
```

#### `lxd_delete_container`
**Description**: Delete an LXD container permanently

**Parameters**:
```json
{
  "name": {
    "type": "string",
    "description": "Container name",
    "required": true
  },
  "host": {
    "type": "string", 
    "description": "LXD host (auto-detected if omitted)"
  },
  "force": {
    "type": "boolean",
    "description": "Force delete running container",
    "default": false
  },
  "delete_snapshots": {
    "type": "boolean",
    "description": "Also delete all snapshots",
    "default": true
  }
}
```

#### `lxd_get_container_status`
**Description**: Get detailed container status and metrics

**Parameters**:
```json
{
  "name": {
    "type": "string",
    "description": "Container name",
    "required": true
  },
  "host": {
    "type": "string",
    "description": "LXD host (auto-detected if omitted)"
  },
  "include_processes": {
    "type": "boolean",
    "description": "Include running processes",
    "default": false
  },
  "include_network": {
    "type": "boolean",
    "description": "Include network information",
    "default": true
  }
}
```

### 4. LXD Container Operations Tools

#### `lxd_exec_container`
**Description**: Execute command in LXD container

**Parameters**:
```json
{
  "name": {
    "type": "string",
    "description": "Container name",
    "required": true
  },
  "command": {
    "type": "string",
    "description": "Command to execute",
    "required": true
  },
  "host": {
    "type": "string",
    "description": "LXD host (auto-detected if omitted)"
  },
  "user": {
    "type": "string", 
    "description": "User to run command as",
    "default": "root"
  },
  "working_directory": {
    "type": "string",
    "description": "Working directory for command",
    "default": "/root"
  },
  "environment": {
    "type": "object",
    "description": "Environment variables"
  },
  "timeout_seconds": {
    "type": "integer", 
    "description": "Command execution timeout",
    "default": 60
  }
}
```

#### `lxd_get_container_logs`
**Description**: Retrieve container logs

**Parameters**:
```json
{
  "name": {
    "type": "string",
    "description": "Container name",
    "required": true
  },
  "host": {
    "type": "string",
    "description": "LXD host (auto-detected if omitted)"
  },
  "lines": {
    "type": "integer",
    "description": "Number of log lines to retrieve",
    "default": 100
  },
  "follow": {
    "type": "boolean",
    "description": "Follow log output (streaming)",
    "default": false
  }
}
```

#### `lxd_upload_file`
**Description**: Upload file to container

**Parameters**:
```json
{
  "name": {
    "type": "string",
    "description": "Container name", 
    "required": true
  },
  "source_path": {
    "type": "string",
    "description": "Local file path",
    "required": true
  },
  "destination_path": {
    "type": "string", 
    "description": "Container file path",
    "required": true
  },
  "host": {
    "type": "string",
    "description": "LXD host (auto-detected if omitted)"
  },
  "permissions": {
    "type": "string",
    "description": "File permissions (e.g., '644')",
    "default": "644"
  },
  "owner": {
    "type": "string",
    "description": "File owner",
    "default": "root"
  }
}
```

#### `lxd_download_file`
**Description**: Download file from container

**Parameters**:
```json
{
  "name": {
    "type": "string",
    "description": "Container name",
    "required": true
  },
  "source_path": {
    "type": "string", 
    "description": "Container file path",
    "required": true
  },
  "destination_path": {
    "type": "string",
    "description": "Local file path",
    "required": true
  },
  "host": {
    "type": "string",
    "description": "LXD host (auto-detected if omitted)"
  }
}
```

### 5. LXD Snapshot & Backup Tools

#### `lxd_create_snapshot`
**Description**: Create container snapshot

**Parameters**:
```json
{
  "name": {
    "type": "string",
    "description": "Container name",
    "required": true  
  },
  "snapshot_name": {
    "type": "string",
    "description": "Snapshot name (auto-generated if omitted)"
  },
  "host": {
    "type": "string",
    "description": "LXD host (auto-detected if omitted)"
  },
  "stateful": {
    "type": "boolean",
    "description": "Include container state (RAM) in snapshot",
    "default": false
  },
  "description": {
    "type": "string",
    "description": "Snapshot description"
  }
}
```

#### `lxd_restore_snapshot`
**Description**: Restore container from snapshot

**Parameters**:
```json
{
  "name": {
    "type": "string",
    "description": "Container name",
    "required": true
  },
  "snapshot_name": {
    "type": "string", 
    "description": "Snapshot name to restore",
    "required": true
  },
  "host": {
    "type": "string",
    "description": "LXD host (auto-detected if omitted)"
  },
  "stateful": {
    "type": "boolean",
    "description": "Restore container state (requires stateful snapshot)",
    "default": false
  }
}
```

#### `lxd_list_snapshots`
**Description**: List container snapshots

**Parameters**:
```json
{
  "name": {
    "type": "string",
    "description": "Container name",
    "required": true
  },
  "host": {
    "type": "string",
    "description": "LXD host (auto-detected if omitted)"
  },
  "include_size": {
    "type": "boolean", 
    "description": "Include snapshot sizes",
    "default": true
  }
}
```

### 6. Hybrid Platform Tools

#### `suggest_platform`
**Description**: Recommend optimal platform (Proxmox vs LXD) for workload

**Parameters**:
```json
{
  "workload_type": {
    "type": "string",
    "enum": ["web_server", "database", "ai_training", "development", "microservice"],
    "description": "Type of workload",
    "required": true
  },
  "requirements": {
    "type": "object",
    "properties": {
      "cores": {"type": "integer"},
      "memory_gb": {"type": "number"},
      "storage_gb": {"type": "integer"},
      "gpu_required": {"type": "boolean"},
      "isolation_level": {"type": "string", "enum": ["container", "vm", "high"]},
      "os_type": {"type": "string", "enum": ["linux", "windows"]},
      "performance_priority": {"type": "string", "enum": ["cost", "performance", "balanced"]}
    }
  }
}
```

**Returns**:
```json
{
  "recommended_platform": "lxd",
  "recommended_host": "192.168.10.101",
  "reasoning": "Lightweight Linux workload with moderate resource needs ideal for container deployment",
  "resource_allocation": {
    "cpu_limit": "2",
    "memory_limit": "4GB",
    "storage_limit": "50GB"
  },
  "alternative_options": [
    {
      "platform": "proxmox",
      "host": "proxmox", 
      "reasoning": "Full VM isolation if security requirements increase"
    }
  ],
  "cost_comparison": {
    "lxd_cost_per_hour": 0.02,
    "proxmox_cost_per_hour": 0.05
  }
}
```

#### `unified_resource_view`
**Description**: Get unified view of all infrastructure resources

**Parameters**:
```json
{
  "include_utilization": {
    "type": "boolean",
    "description": "Include resource utilization metrics",
    "default": true
  },
  "group_by": {
    "type": "string",
    "enum": ["platform", "location", "workload_type"],
    "description": "How to group the results",
    "default": "platform"
  }
}
```

#### `migrate_container_to_vm`
**Description**: Migrate LXD container to Proxmox VM

**Parameters**:
```json
{
  "container_name": {
    "type": "string",
    "description": "Source container name",
    "required": true
  },
  "source_host": {
    "type": "string",
    "description": "Source LXD host"
  },
  "destination_host": {
    "type": "string",
    "description": "Destination Proxmox host",
    "default": "proxmox"
  },
  "vm_name": {
    "type": "string",
    "description": "Target VM name (defaults to container name)"
  },
  "preserve_snapshots": {
    "type": "boolean",
    "description": "Migrate container snapshots as VM snapshots",
    "default": true
  },
  "shutdown_source": {
    "type": "boolean",
    "description": "Shutdown source container after migration",
    "default": true
  }
}
```

## Natural Language Query Examples

The LXD tools support natural language queries similar to Proxmox tools:

```bash
# Container Discovery
"show lxd containers"           → lxd_list_containers()
"running ubuntu containers"     → lxd_list_containers(status="running", image="ubuntu*")
"containers on pi-01"          → lxd_list_containers(host="192.168.10.101")
"container web-server"         → lxd_get_container_status(name="web-server")
"containers with 2gb ram"      → lxd_list_containers(min_memory_mb=2048)

# Container Management  
"create container nginx-server" → lxd_create_container(name="nginx-server")
"start container database"     → lxd_start_container(name="database")
"stop container test-env"      → lxd_stop_container(name="test-env")
"delete container old-app"     → lxd_delete_container(name="old-app")

# Platform Intelligence
"suggest platform for web app" → suggest_platform(workload_type="web_server")
"show all infrastructure"      → unified_resource_view()
"migrate web-server to vm"     → migrate_container_to_vm(container_name="web-server")

# LXD Setup
"setup lxd on 192.168.10.101"  → setup_lxd_host(host="192.168.10.101")
"discover lxd hosts"           → discover_lxd_hosts()
"test lxd connection"          → test_lxd_connection()
```

## Error Handling Standards

All LXD tools follow consistent error handling patterns:

```json
{
  "success": false,
  "error_code": "LXD_CONTAINER_NOT_FOUND",
  "error_message": "Container 'web-server' not found on host '192.168.10.101'",
  "details": {
    "host": "192.168.10.101",
    "container_name": "web-server",
    "available_containers": ["database", "dev-env"]
  },
  "suggestions": [
    "Check container name spelling",
    "Use 'lxd_list_containers' to see available containers",
    "Specify correct host with 'host' parameter"
  ]
}
```

## Performance Considerations

- **Connection Pooling**: SSH connections and LXD API sessions are reused
- **Parallel Operations**: Operations across multiple hosts run concurrently  
- **Caching**: Container and image lists cached with 5-minute TTL
- **Lazy Loading**: Detailed information loaded only when requested
- **Rate Limiting**: Respects LXD API rate limits (100 req/min per host)

## Security Features

- **SSH Key Authentication**: No password authentication supported
- **Certificate Validation**: LXD API certificates verified
- **Privilege Isolation**: Unprivileged containers by default
- **Network Segmentation**: Container networks isolated by default
- **Audit Logging**: All container operations logged with timestamps

This comprehensive tool set enables AI agents to manage LXD containers with the same sophistication as Proxmox VMs, while providing intelligent hybrid infrastructure management capabilities.