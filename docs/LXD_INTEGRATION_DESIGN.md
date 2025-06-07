# LXD Integration Design Document

## Overview
This document outlines the design for integrating LXD (Linux Containers) support into the MCP Python server, extending the existing Proxmox infrastructure management capabilities to include lightweight container orchestration on Raspberry Pi and other ARM64/x86_64 systems.

## Architecture

### Multi-Platform Provider Design
```
User Request → AI Agent → Agnostic Config → Provider Router → [Proxmox Driver | LXD Driver]
                   ↓                              ↓                    ↓
              (decisions)                   (route decision)    (implementation)
                   ↓                              ↓                    ↓
              Inventory ←  Validation  ←  Platform Detection ←  Provider APIs
```

### Provider Selection Logic
- **VMs + Full Virtualization** → Proxmox
- **Lightweight Containers** → LXD  
- **Application Containers** → Docker (existing)
- **Hybrid Workloads** → Intelligent placement across both

## LXD Integration Components

### 1. LXD Discovery Wizard (`src/tools/lxd_setup_wizard.py`)

#### Discovery Flow:
1. **SSH Connection Test** - Connect to target Pi/server
2. **LXD Detection** - Check if LXD is installed (`lxd --version`)
3. **Installation Prompt** - Ask user if they want to install LXD
4. **Automated Installation** - Install via snap or apt
5. **Initial Configuration** - Run `lxd init` with sensible defaults
6. **Credential Storage** - Store SSH credentials securely
7. **Discovery Registration** - Add to MCP inventory

#### Installation Methods:
- **Snap (Preferred)**: `sudo snap install lxd`
- **APT (Fallback)**: `sudo apt install lxd lxd-client`
- **Version Detection**: Choose method based on OS version

### 2. LXD API Client (`src/utils/lxd_api.py`)

#### API Architecture:
```python
class LXDAPIClient:
    def __init__(self, host, ssh_user, ssh_key_path, port=8443):
        # LXD uses HTTPS REST API over SSH tunnel or direct HTTPS
        
    # Core API Methods
    async def authenticate()
    async def get_containers()
    async def get_images() 
    async def get_networks()
    async def get_storage_pools()
    async def get_cluster_members()
    
    # Container Lifecycle
    async def create_container()
    async def start_container()
    async def stop_container()
    async def delete_container()
    async def get_container_state()
    
    # Resource Management
    async def get_host_resources()
    async def set_container_limits()
    async def get_container_logs()
```

#### Connection Methods:
- **SSH Tunnel**: Secure connection through SSH (recommended for Pi)
- **Direct HTTPS**: For local network access with certificates
- **Unix Socket**: For local access (when MCP runs on same host)

### 3. LXD Discovery Tools (`src/tools/lxd_discovery.py`)

#### Discovery Capabilities:
- **Container Inventory**: Running/stopped containers with resource usage
- **Image Repository**: Available images (Ubuntu, Alpine, etc.)
- **Network Configuration**: Bridges, VLANs, IP allocation
- **Storage Pools**: ZFS, BTRFS, directory storage
- **Cluster Status**: Multi-node LXD cluster information
- **Resource Limits**: CPU, memory, disk quotas per container

#### Natural Language Queries:
```bash
"show lxd containers"           → List all containers
"running ubuntu containers"     → Filter by OS and status  
"container web-server"          → Get specific container details
"lxd storage pools"             → Show storage configuration
"containers with 1gb ram"       → Filter by resource allocation
```

### 4. LXD Container Management (`src/tools/lxd_containers.py`)

#### Container Operations:
```python
# Container Creation
async def create_lxd_container(
    name: str,
    image: str = "ubuntu:22.04",
    cpu_limit: str = "1",
    memory_limit: str = "1GB", 
    disk_limit: str = "10GB",
    network: str = "lxdbr0",
    profiles: List[str] = ["default"],
    config: Dict[str, str] = None
) -> Dict[str, Any]

# Container Lifecycle
async def start_lxd_container(name: str) -> Dict[str, Any]
async def stop_lxd_container(name: str, force: bool = False) -> Dict[str, Any]
async def restart_lxd_container(name: str) -> Dict[str, Any]
async def delete_lxd_container(name: str, force: bool = False) -> Dict[str, Any]

# Container Information
async def get_lxd_container_status(name: str) -> Dict[str, Any]
async def get_lxd_container_logs(name: str, lines: int = 100) -> Dict[str, Any]
async def exec_lxd_container(name: str, command: str) -> Dict[str, Any]
```

#### Profile Management:
- **Default Profile**: Basic networking and storage
- **Web Server Profile**: Port forwarding, resource limits
- **Database Profile**: Persistent storage, memory limits
- **Development Profile**: Bind mounts, privileged access

## Multi-Platform Resource Allocation

### Intelligent Placement Algorithm:
```python
def select_platform_for_workload(workload_type: str, resources: Dict) -> str:
    """
    Choose between Proxmox VMs and LXD containers based on workload needs.
    """
    # Full OS isolation needed → Proxmox VM
    if workload_type in ["windows", "complex_networking", "gpu_passthrough"]:
        return "proxmox"
    
    # Lightweight Linux workload → LXD Container  
    if workload_type in ["web_server", "database", "microservice", "development"]:
        return "lxd"
    
    # Resource-based decision
    if resources.get("memory_gb", 0) > 8 or resources.get("cores", 0) > 4:
        return "proxmox"  # Heavy workload
    else:
        return "lxd"      # Lightweight workload
```

### Resource Discovery:
- **Proxmox Nodes**: Full x86_64 virtualization capability
- **LXD Hosts**: ARM64 Raspberry Pi + x86_64 container hosts
- **Unified Inventory**: Single view of all compute resources
- **Cross-Platform Networking**: VPN/overlay networks between platforms

## MCP Tool Specifications

### LXD Setup Tools:
- `setup_lxd_host` - Install and configure LXD on target host
- `discover_lxd_hosts` - Find existing LXD installations on network
- `test_lxd_connection` - Verify API connectivity and authentication

### LXD Discovery Tools:
- `lxd_list_hosts` - Show all LXD hosts in inventory
- `lxd_list_containers` - Show containers with filtering support
- `lxd_list_images` - Available container images
- `lxd_list_networks` - Network configuration
- `lxd_list_storage` - Storage pools and usage

### LXD Management Tools:
- `lxd_create_container` - Create new container from image
- `lxd_start_container` - Start stopped container
- `lxd_stop_container` - Stop running container  
- `lxd_delete_container` - Remove container permanently
- `lxd_get_container_status` - Detailed container information
- `lxd_exec_container` - Execute commands in container
- `lxd_get_container_logs` - Retrieve container logs

### Hybrid Platform Tools:
- `suggest_platform` - Recommend Proxmox vs LXD for workload
- `migrate_container_to_vm` - Convert LXD container to Proxmox VM
- `unified_resource_view` - Show all platforms in single view

## Configuration Management

### Credential Storage:
```json
{
  "lxd_hosts": {
    "pi-cluster-01": {
      "host": "192.168.10.101", 
      "ssh_user": "ubuntu",
      "ssh_key_path": "/home/user/.ssh/id_rsa",
      "api_port": 8443,
      "cluster_member": true
    },
    "pi-cluster-02": {
      "host": "192.168.10.102",
      "ssh_user": "ubuntu", 
      "ssh_key_path": "/home/user/.ssh/id_rsa",
      "api_port": 8443,
      "cluster_member": true
    }
  }
}
```

### Profile Templates:
```yaml
# Web Server Profile
name: webserver
config:
  limits.cpu: "2"
  limits.memory: "2GB"
  limits.memory.swap: "false"
devices:
  eth0:
    type: nic
    nictype: bridged
    parent: lxdbr0
  http:
    type: proxy
    listen: tcp:0.0.0.0:80
    connect: tcp:127.0.0.1:80
  https:
    type: proxy
    listen: tcp:0.0.0.0:443
    connect: tcp:127.0.0.1:443
```

## Error Handling & Recovery

### Common Scenarios:
- **SSH Connection Failed** → Retry with different credentials
- **LXD Not Installed** → Offer installation wizard
- **API Authentication Failed** → Re-run credential setup
- **Container Creation Failed** → Check resource availability
- **Network Issues** → Fallback to different network configuration

### Graceful Degradation:
- **Single Host Down** → Continue with remaining hosts
- **API Unavailable** → Switch to SSH command execution
- **Storage Full** → Suggest cleanup or expansion

## Testing Strategy

### Unit Tests:
- LXD API client connection and authentication
- Container lifecycle operations
- Resource discovery and filtering
- Error handling and recovery

### Integration Tests:  
- Full wizard flow from discovery to container creation
- Multi-host cluster operations
- Proxmox + LXD hybrid scenarios
- Network configuration and connectivity

### Mock Infrastructure:
- Simulated LXD API responses
- SSH connection mocking
- Container state simulation
- Resource usage simulation

## Performance Considerations

### Optimization Strategies:
- **Connection Pooling**: Reuse SSH connections and API sessions
- **Caching**: Cache container and image lists with TTL
- **Parallel Operations**: Concurrent operations across multiple hosts
- **Lazy Loading**: Load detailed information only when requested

### Resource Monitoring:
- **Pi Resource Limits**: Monitor ARM CPU and limited RAM
- **Network Bandwidth**: Efficient data transfer over SSH tunnels
- **API Rate Limiting**: Respect LXD API limits

## Security Considerations

### Access Control:
- **SSH Key Authentication**: No password authentication
- **LXD Group Membership**: Secure API access
- **Container Isolation**: Proper unprivileged containers
- **Network Segmentation**: Isolated container networks

### Credential Management:
- **Encrypted Storage**: SSH keys encrypted at rest
- **Minimal Privileges**: Least privilege access for operations
- **Audit Logging**: Track all container operations
- **Certificate Management**: Proper TLS for API connections

## Future Extensions

### Advanced Features:
- **Container Migration**: Live migration between LXD hosts
- **Cluster Management**: Multi-Pi LXD cluster orchestration
- **Image Building**: Custom container image creation
- **Backup/Restore**: Automated container backup strategies
- **Monitoring Integration**: Prometheus/Grafana for container metrics

### Integration Opportunities:
- **Kubernetes**: LXD as container runtime for lightweight K8s
- **Ansible Integration**: Container configuration management
- **CI/CD Pipelines**: Ephemeral containers for testing
- **Edge Computing**: Distributed container workloads

---

This design provides a comprehensive foundation for LXD integration that mirrors the existing Proxmox capabilities while leveraging the unique advantages of lightweight containerization for ARM64 and resource-constrained environments.