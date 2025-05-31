# Enhanced Hardware Discovery & AI Deployment Intelligence

## 🎯 **The Vision: Smart Infrastructure Management**

Instead of just "list VMs", we want:
- **"Where should I deploy an Ollama training server?"** → "Node 'proxmox' has MI50 GPU, recommend there"
- **"Optimize my VM placement"** → "Move VM 998 to free up GPU node for AI workloads"
- **"What's the best node for a database?"** → "Node 'storage-1' has NVMe drives, lowest latency"

## 🔬 **Hardware Discovery We Need**

### **GPU Detection**
```json
{
  "node": "proxmox",
  "gpus": [
    {
      "id": "0000:03:00.0",
      "model": "AMD Radeon Instinct MI50",
      "memory": "16GB HBM2",
      "compute_units": 60,
      "vram_used": "2GB",
      "vram_total": "16GB",
      "temperature": "65C",
      "power_usage": "150W",
      "driver": "amdgpu",
      "opencl": true,
      "rocm": true,
      "suitable_for": ["ai_training", "compute", "mining"],
      "current_allocation": null
    }
  ]
}
```

### **CPU Details**
```json
{
  "cpu": {
    "model": "AMD Ryzen 9 5950X",
    "cores": 16,
    "threads": 32,
    "base_freq": "3.4GHz", 
    "boost_freq": "4.9GHz",
    "architecture": "Zen 3",
    "features": ["AVX2", "AES", "virtualization"],
    "tdp": "105W",
    "suitable_for": ["general_compute", "compilation", "virtualization"]
  }
}
```

### **Memory Configuration**
```json
{
  "memory": {
    "total": "64GB",
    "type": "DDR4",
    "speed": "3200MHz",
    "channels": 4,
    "dimms": [
      {"slot": "A1", "size": "16GB", "speed": "3200MHz"},
      {"slot": "A2", "size": "16GB", "speed": "3200MHz"},
      {"slot": "B1", "size": "16GB", "speed": "3200MHz"},
      {"slot": "B2", "size": "16GB", "speed": "3200MHz"}
    ],
    "ecc": false
  }
}
```

### **Storage Details**
```json
{
  "storage": [
    {
      "device": "/dev/nvme0n1",
      "type": "NVMe SSD",
      "model": "Samsung 970 EVO Plus",
      "size": "1TB",
      "read_speed": "3500MB/s",
      "write_speed": "3300MB/s",
      "wear_level": "2%",
      "suitable_for": ["databases", "vm_storage", "high_iops"]
    },
    {
      "device": "/dev/sdb",
      "type": "SATA HDD",
      "model": "Seagate Barracuda",
      "size": "4TB", 
      "read_speed": "180MB/s",
      "write_speed": "180MB/s",
      "suitable_for": ["backup", "archive", "bulk_storage"]
    }
  ]
}
```

### **Network Capabilities**
```json
{
  "network": [
    {
      "interface": "eth0",
      "type": "Gigabit Ethernet",
      "speed": "1Gbps",
      "suitable_for": ["general", "management"]
    },
    {
      "interface": "eth1", 
      "type": "10 Gigabit Ethernet",
      "speed": "10Gbps",
      "suitable_for": ["storage", "migration", "high_throughput"]
    }
  ]
}
```

## 🧠 **AI Deployment Intelligence**

### **Workload Characterization**
```python
WORKLOAD_PROFILES = {
    "ollama_training": {
        "requires": ["gpu", "high_memory"],
        "prefers": ["nvme_storage", "high_cpu_freq"],
        "memory_min": "16GB",
        "gpu_memory_min": "8GB",
        "cpu_cores_min": 8
    },
    "mysql_database": {
        "requires": ["fast_storage"],
        "prefers": ["nvme_storage", "high_memory"],
        "memory_min": "8GB", 
        "storage_type": "nvme",
        "cpu_cores_min": 4
    },
    "web_server": {
        "requires": ["network"],
        "prefers": ["fast_cpu"],
        "memory_min": "2GB",
        "cpu_cores_min": 2,
        "network_min": "1Gbps"
    }
}
```

### **Smart Placement Algorithm**
```python
def suggest_deployment(workload_type: str, nodes: List[Node]) -> DeploymentSuggestion:
    """AI-powered workload placement."""
    
    profile = WORKLOAD_PROFILES[workload_type]
    scored_nodes = []
    
    for node in nodes:
        score = 0
        reasons = []
        
        # Check requirements (must-have)
        if "gpu" in profile["requires"]:
            if node.gpus:
                score += 100
                reasons.append(f"Has {node.gpus[0].model} GPU")
            else:
                continue  # Skip nodes without required GPU
        
        # Check preferences (nice-to-have)
        if "nvme_storage" in profile["prefers"]:
            nvme_count = len([s for s in node.storage if s.type == "NVMe SSD"])
            score += nvme_count * 20
            if nvme_count > 0:
                reasons.append(f"Has {nvme_count} NVMe drives")
        
        # Resource availability
        memory_available = node.memory.total - node.memory.used
        if memory_available >= parse_memory(profile["memory_min"]):
            score += 50
        else:
            score -= 100  # Penalty for insufficient memory
        
        # Current utilization (prefer less loaded nodes)
        utilization_penalty = node.cpu_usage * 30
        score -= utilization_penalty
        
        scored_nodes.append({
            "node": node.name,
            "score": score,
            "reasons": reasons,
            "warnings": check_deployment_warnings(node, profile)
        })
    
    # Sort by score and return best suggestion
    scored_nodes.sort(key=lambda x: x["score"], reverse=True)
    return DeploymentSuggestion(scored_nodes)
```

### **Migration Optimization**
```python
def suggest_vm_migration(nodes: List[Node]) -> List[MigrationSuggestion]:
    """Suggest VM moves for better resource utilization."""
    
    suggestions = []
    
    # Find underutilized nodes
    underutilized = [n for n in nodes if n.cpu_usage < 0.3 and n.memory_usage < 0.5]
    
    # Find overutilized nodes  
    overutilized = [n for n in nodes if n.cpu_usage > 0.8 or n.memory_usage > 0.8]
    
    for busy_node in overutilized:
        for vm in busy_node.vms:
            # Skip VMs that need special hardware
            if vm_needs_gpu(vm) and not any(n.gpus for n in underutilized):
                continue
                
            for target_node in underutilized:
                if can_migrate(vm, target_node):
                    benefit = calculate_migration_benefit(vm, busy_node, target_node)
                    suggestions.append(MigrationSuggestion(
                        vm=vm.name,
                        from_node=busy_node.name,
                        to_node=target_node.name,
                        benefit=benefit,
                        reason=f"Free up {vm.cpu_cores} cores on overloaded node"
                    ))
    
    return sorted(suggestions, key=lambda x: x.benefit, reverse=True)
```

## 🛠️ **Implementation Plan**

### **Phase 1: Enhanced Hardware Discovery**
```python
# Add to ProxmoxAPIClient
async def discover_hardware(self, node_name: str) -> NodeHardware:
    """Discover detailed hardware capabilities."""
    
    hardware = NodeHardware()
    
    # GPU discovery via Proxmox API + direct commands
    hardware.gpus = await self._discover_gpus(node_name)
    
    # CPU details from /proc/cpuinfo
    hardware.cpu = await self._discover_cpu_details(node_name)
    
    # Memory configuration
    hardware.memory = await self._discover_memory_config(node_name)
    
    # Storage capabilities
    hardware.storage = await self._discover_storage_details(node_name)
    
    # Network interfaces
    hardware.network = await self._discover_network_capabilities(node_name)
    
    return hardware
```

### **Phase 2: AI Deployment Advisor**
```python
# New MCP tools
@tool("suggest_deployment")
async def suggest_deployment(workload_type: str, requirements: dict = None):
    """Suggest best node for deploying a specific workload."""
    
@tool("optimize_placement") 
async def optimize_placement():
    """Analyze current VM placement and suggest optimizations."""
    
@tool("check_capacity")
async def check_capacity(workload_requirements: dict):
    """Check if cluster has capacity for new workload."""
```

### **Phase 3: VM Management Tools**
```python
@tool("create_vm")
async def create_vm(name: str, workload_type: str, node: str = None):
    """Create VM with optimal configuration for workload type."""
    
@tool("migrate_vm") 
async def migrate_vm(vm_id: int, target_node: str, reason: str):
    """Migrate VM to different node with validation."""
    
@tool("resize_vm")
async def resize_vm(vm_id: int, new_specs: dict):
    """Resize VM resources based on usage patterns."""
```

## 🎯 **User Experience Examples**

### **Intelligent Deployment**
```
User: "I want to deploy an Ollama server for AI training"

AI Analysis:
- Workload requires: GPU, high memory (16GB+)
- Node 'proxmox' has: MI50 GPU (16GB VRAM), 64GB RAM
- Current utilization: 28% CPU, 45% memory
- GPU: Available (no current allocation)

Recommendation: "Deploy on node 'proxmox'"
Reasons:
✅ AMD MI50 GPU perfect for AI training
✅ 48GB RAM available (exceeds 16GB requirement) 
✅ Node underutilized (plenty of capacity)
⚠️ Consider moving VM 998 first to free up more resources
```

### **Migration Optimization**
```
User: "Optimize my VM placement"

AI Analysis:
Current State:
- Node 'proxmox': 85% CPU, 70% memory (overloaded)
- VMs: ollama-server (8 cores), mysql-test (2 cores), prod-db (4 cores)
- GPU: Only ollama-server needs it

Suggestions:
1. Move 'mysql-test' to node 'storage-1' 
   ↳ Frees 2 cores, doesn't need GPU
2. Move 'prod-db' to node 'compute-2'
   ↳ Frees 4 cores, gets faster NVMe storage
   
Result: 70% → 45% CPU utilization on main node
```

## 📊 **Implementation Priorities**

### **High Priority (Next 2 weeks)**
1. ✅ GPU discovery (MI50 detection)
2. ✅ Storage type detection (NVMe vs SATA)
3. ✅ Basic deployment suggestions
4. ✅ VM creation tools

### **Medium Priority (Following 2 weeks)**  
1. CPU model/feature detection
2. Memory configuration details
3. Migration optimization suggestions
4. Application installation tools

### **Low Priority (Future)**
1. Network bandwidth testing
2. Performance benchmarking
3. Predictive capacity planning
4. Multi-cluster management

This transforms the MCP from "VM listing tool" to "intelligent infrastructure advisor" - exactly what you need for smart AI workload deployment! 🚀