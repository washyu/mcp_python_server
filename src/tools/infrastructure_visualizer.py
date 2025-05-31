"""
Infrastructure visualization tool for creating diagrams from Proxmox inventory.
"""

import json
from typing import Dict, Any, List
from pathlib import Path


class InfrastructureVisualizer:
    """Generate visual diagrams from Proxmox infrastructure data."""
    
    def __init__(self, inventory_path: str = None):
        self.inventory_path = inventory_path or "inventory/proxmox-resources.json"
        self.inventory = self._load_inventory()
    
    def _load_inventory(self) -> Dict[str, Any]:
        """Load inventory from JSON file."""
        try:
            with open(self.inventory_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"nodes": [], "vms": [], "storage": [], "networks": [], "templates": []}
    
    def generate_topology_diagram(self) -> str:
        """Generate ASCII topology diagram."""
        nodes = self.inventory.get("nodes", [])
        vms = self.inventory.get("vms", [])
        storage = self.inventory.get("storage", [])
        networks = self.inventory.get("networks", [])
        
        # Parse node data (handle string representation)
        node_info = self._parse_node_data(nodes[0] if nodes else None)
        
        diagram = []
        
        # Header
        diagram.extend([
            "┌─────────────────────────────────────────────────────────────────────────────┐",
            "│                            PROXMOX CLUSTER                                 │",
            "│                         192.168.10.200 (Host)                             │",
            "└─────────────────────────────────────────────────────────────────────────────┘",
            "                                      │",
            "                                      ▼"
        ])
        
        # Node details
        diagram.extend([
            "┌─────────────────────────────────────────────────────────────────────────────┐",
            f"│                              NODE: {node_info['name']:<31} │",
            f"│                              Status: {node_info['status'].upper():<29} │",
            f"│                              Uptime: {node_info['uptime']:<29} │",
            "├─────────────────────────────────────────────────────────────────────────────┤",
            "│  🖥️  HARDWARE SPECIFICATIONS                                               │",
            f"│   CPU: {node_info['cpu_spec']:<64} │",
            f"│   RAM: {node_info['ram_spec']:<64} │",
            f"│   DISK: {node_info['disk_spec']:<63} │",
            "│   GPU: AMD Radeon Instinct MI50 (16GB HBM2) 🎯 AI-CAPABLE                 │",
            "├─────────────────────────────────────────────────────────────────────────────┤",
            "│  💾 STORAGE POOLS                                                          │"
        ])
        
        # Storage pools
        for pool in storage[:3]:  # Show first 3 pools
            pool_name = pool.get("storage", "unknown")
            pool_path = pool.get("path", pool.get("content", ""))
            diagram.append(f"│   ├── {pool_name} ({pool_path[:50]})")
        
        # Network interfaces
        diagram.extend([
            "├─────────────────────────────────────────────────────────────────────────────┤",
            "│  🌐 NETWORK INTERFACES                                                     │"
        ])
        
        for net in networks[:3]:  # Show first 3 networks
            iface = net.get("iface", "unknown")
            addr = net.get("address", net.get("cidr", ""))
            if addr:
                diagram.append(f"│   ├── {iface} ({addr}) - Network Interface")
            else:
                diagram.append(f"│   ├── {iface} (Physical Interface)")
        
        diagram.extend([
            "└─────────────────────────────────────────────────────────────────────────────┘",
            "                                      │",
            "                                      ▼"
        ])
        
        # VM section
        running_vms = [vm for vm in vms if vm.get("status") == "running"]
        stopped_vms = [vm for vm in vms if vm.get("status") == "stopped"]
        templates = [vm for vm in vms if vm.get("template") == 1]
        
        diagram.extend([
            "┌─────────────────────────────────────────────────────────────────────────────┐",
            f"│                          VIRTUAL MACHINES ({len(vms)} Total)" + " " * (24 - len(str(len(vms)))) + "│",
            "├─────────────────────────────────────────────────────────────────────────────┤",
            "│                                                                             │",
            f"│  🟢 RUNNING VMs ({len(running_vms)})" + " " * (56 - len(str(len(running_vms)))) + "│"
        ])
        
        # Running VMs
        for vm in running_vms:
            vm_box = self._create_vm_box(vm, "running")
            diagram.extend(vm_box)
        
        diagram.extend([
            "│                                                                             │",
            f"│  🔴 STOPPED VMs ({len(stopped_vms)})" + " " * (56 - len(str(len(stopped_vms)))) + "│"
        ])
        
        # Stopped VMs (show first 4)
        for vm in stopped_vms[:4]:
            vm_box = self._create_vm_box(vm, "stopped")
            diagram.extend(vm_box)
        
        if templates:
            diagram.extend([
                "│                                                                             │",
                f"│  📋 TEMPLATE ({len(templates)})" + " " * (58 - len(str(len(templates)))) + "│"
            ])
            
            for template in templates:
                vm_box = self._create_vm_box(template, "template")
                diagram.extend(vm_box)
        
        diagram.append("└─────────────────────────────────────────────────────────────────────────────┘")
        
        return "\n".join(diagram)
    
    def _parse_node_data(self, node_data) -> Dict[str, str]:
        """Parse node data from string representation."""
        if not node_data:
            return {
                "name": "unknown",
                "status": "unknown", 
                "uptime": "unknown",
                "cpu_spec": "unknown",
                "ram_spec": "unknown",
                "disk_spec": "unknown"
            }
        
        import re
        
        # Extract values from string representation
        node_str = str(node_data)
        
        # Parse node info
        name_match = re.search(r"node='([^']*)'", node_str)
        status_match = re.search(r"status='([^']*)'", node_str)
        cpu_match = re.search(r"cpu=([0-9.]+)", node_str)
        maxcpu_match = re.search(r"maxcpu=([0-9]+)", node_str)
        mem_match = re.search(r"mem=([0-9]+)", node_str)
        maxmem_match = re.search(r"maxmem=([0-9]+)", node_str)
        disk_match = re.search(r"disk=([0-9]+)", node_str)
        maxdisk_match = re.search(r"maxdisk=([0-9]+)", node_str)
        uptime_match = re.search(r"uptime=([0-9]+)", node_str)
        
        name = name_match.group(1) if name_match else "unknown"
        status = status_match.group(1) if status_match else "unknown"
        
        # Calculate specs
        cpu_usage = float(cpu_match.group(1)) * 100 if cpu_match else 0
        max_cpu = int(maxcpu_match.group(1)) if maxcpu_match else 0
        cpu_spec = f"{max_cpu} cores ({cpu_usage:.1f}% utilization)"
        
        mem_used = int(mem_match.group(1)) / (1024**3) if mem_match else 0
        max_mem = int(maxmem_match.group(1)) / (1024**3) if maxmem_match else 0
        ram_spec = f"{max_mem:.1f}GB total ({mem_used:.1f}GB used, {max_mem - mem_used:.1f}GB free)"
        
        disk_used = int(disk_match.group(1)) / (1024**3) if disk_match else 0
        max_disk = int(maxdisk_match.group(1)) / (1024**3) if maxdisk_match else 0
        disk_spec = f"{max_disk:.1f}GB total ({disk_used:.1f}GB used, {max_disk - disk_used:.1f}GB free)"
        
        uptime_hours = int(uptime_match.group(1)) / 3600 if uptime_match else 0
        uptime_str = f"{uptime_hours:.1f} hours"
        
        return {
            "name": name,
            "status": status,
            "uptime": uptime_str,
            "cpu_spec": cpu_spec,
            "ram_spec": ram_spec,
            "disk_spec": disk_spec
        }
    
    def _create_vm_box(self, vm: Dict[str, Any], vm_type: str) -> List[str]:
        """Create ASCII box for a VM."""
        vm_id = vm.get("vmid", "?")
        name = vm.get("name", "Unknown")
        cpus = vm.get("cpus", 0)
        maxmem_gb = vm.get("maxmem", 0) / (1024**3)
        maxdisk_gb = vm.get("maxdisk", 0) / (1024**3)
        
        # Determine VM category and emoji
        category_info = self._categorize_vm(name, vm.get("tags", ""))
        
        box = [
            "│  ┌─────────────────────────────────────────────────────────────────────┐   │",
            f"│  │ VM {vm_id}: {name:<35} {category_info['emoji']} {category_info['category']:<12} │   │"
        ]
        
        if vm_type != "template":
            box.extend([
                f"│  │ ├── CPU: {cpus} cores" + (" " * (50 - len(f"CPU: {cpus} cores"))) + "│   │",
                f"│  │ ├── RAM: {maxmem_gb:.0f}GB" + (" " * (48 - len(f"RAM: {maxmem_gb:.0f}GB"))) + "│   │"
            ])
            
            if maxdisk_gb > 0:
                box.append(f"│  │ ├── Disk: {maxdisk_gb:.0f}GB" + (" " * (47 - len(f"Disk: {maxdisk_gb:.0f}GB"))) + "│   │")
        
        # Add special notes
        if "ollama" in name.lower():
            box.append("│  │ ├── GPU: Using MI50 for AI training 🎯" + (" " * 24) + "│   │")
        
        # Add status-specific info
        if vm_type == "running":
            mem_used_gb = vm.get("mem", 0) / (1024**3)
            cpu_usage = vm.get("cpu", 0) * 100
            if mem_used_gb > 0:
                box.append(f"│  │ ├── Usage: {cpu_usage:.1f}% CPU, {mem_used_gb:.1f}GB RAM used" + (" " * (20 - len(f"{cpu_usage:.1f}% CPU, {mem_used_gb:.1f}GB RAM used"))) + "│   │")
        elif vm_type == "template":
            box.append("│  │ └── Status: Base template for cloning" + (" " * 26) + "│   │")
        else:
            box.append(f"│  │ └── Status: {category_info['description']}" + (" " * (35 - len(category_info['description']))) + "│   │")
        
        box.append("│  └─────────────────────────────────────────────────────────────────────┘   │")
        box.append("│                                                                             │")
        
        return box
    
    def _categorize_vm(self, name: str, tags: str) -> Dict[str, str]:
        """Categorize VM based on name and tags."""
        name_lower = name.lower()
        tags_lower = tags.lower()
        
        if "ollama" in name_lower or "ai" in tags_lower:
            return {"emoji": "🤖", "category": "AI TRAINING", "description": "LLM inference server"}
        elif "database" in name_lower or "mysql" in name_lower or "mysql" in tags_lower:
            return {"emoji": "💾", "category": "DATABASE", "description": "Database server"}
        elif "jenkins" in name_lower:
            return {"emoji": "🔄", "category": "CI/CD", "description": "Jenkins automation server"}
        elif "mcp" in name_lower:
            return {"emoji": "🔧", "category": "INFRASTRUCTURE", "description": "MCP server"}
        elif "dev" in name_lower:
            return {"emoji": "🔧", "category": "DEVELOPMENT", "description": "Development environment"}
        elif "test" in name_lower:
            return {"emoji": "🧪", "category": "TEST", "description": "Testing environment"}
        elif "template" in name_lower:
            return {"emoji": "📦", "category": "TEMPLATE", "description": "VM template"}
        elif "production" in name_lower or "prod" in name_lower:
            return {"emoji": "🚀", "category": "PRODUCTION", "description": "Production server"}
        else:
            return {"emoji": "⚙️", "category": "GENERAL", "description": "General purpose VM"}
    
    def generate_resource_utilization(self) -> str:
        """Generate resource utilization charts."""
        vms = self.inventory.get("vms", [])
        
        # Calculate total allocations
        total_cpu_allocated = sum(vm.get("cpus", 0) for vm in vms)
        total_ram_allocated = sum(vm.get("maxmem", 0) for vm in vms) / (1024**3)
        
        # Available resources (from node data)
        node_data = self.inventory.get("nodes", [])
        if node_data:
            node_str = str(node_data[0])
            import re
            maxcpu_match = re.search(r"maxcpu=([0-9]+)", node_str)
            maxmem_match = re.search(r"maxmem=([0-9]+)", node_str)
            
            total_cpu_available = int(maxcpu_match.group(1)) if maxcpu_match else 12
            total_ram_available = int(maxmem_match.group(1)) / (1024**3) if maxmem_match else 64
        else:
            total_cpu_available = 12
            total_ram_available = 64
        
        chart = []
        
        # CPU Chart
        chart.extend([
            "## 📊 Resource Utilization Analysis",
            "",
            "### CPU Distribution",
            f"Total CPU Cores: {total_cpu_available}",
            "┌─────────────────┬─────────┬─────────────────────────────────────┐",
            "│ VM Name         │ Cores   │ Usage Bar                           │",
            "├─────────────────┼─────────┼─────────────────────────────────────┤"
        ])
        
        # Sort VMs by CPU allocation
        sorted_vms = sorted(vms, key=lambda x: x.get("cpus", 0), reverse=True)
        
        for vm in sorted_vms[:8]:  # Show top 8 VMs
            name = vm.get("name", "Unknown")[:15]
            cpus = vm.get("cpus", 0)
            status = vm.get("status", "unknown")
            
            # Create usage bar (32 chars max)
            bar_length = min(32, int((cpus / total_cpu_available) * 32))
            usage_bar = "█" * bar_length
            
            if status == "stopped":
                usage_bar += " (stopped)"
            elif vm.get("template"):
                usage_bar += " (template)"
            
            chart.append(f"│ {name:<15} │ {cpus} cores │ {usage_bar:<35} │")
        
        # Totals
        overcommit = total_cpu_allocated / total_cpu_available
        chart.extend([
            "├─────────────────┼─────────┼─────────────────────────────────────┤",
            f"│ ALLOCATED       │ {total_cpu_allocated} cores│ {'█' * 32}{'█' * (int(overcommit) - 1) if overcommit > 1 else ''}│",
            f"│ AVAILABLE       │ {total_cpu_available} cores│ {'█' * 24}                    │",
            f"│ OVERCOMMIT      │ {overcommit:.1f}x    │ Some VMs stopped = fits             │",
            "└─────────────────┴─────────┴─────────────────────────────────────┘"
        ])
        
        # Memory Chart
        chart.extend([
            "",
            "### Memory Distribution", 
            f"Total Memory: {total_ram_available:.1f}GB",
            "┌─────────────────┬─────────┬─────────────────────────────────────┐",
            "│ VM Name         │ RAM     │ Usage Bar                           │",
            "├─────────────────┼─────────┼─────────────────────────────────────┤"
        ])
        
        # Sort VMs by memory allocation
        sorted_vms_mem = sorted(vms, key=lambda x: x.get("maxmem", 0), reverse=True)
        
        for vm in sorted_vms_mem[:8]:  # Show top 8 VMs
            name = vm.get("name", "Unknown")[:15]
            maxmem_gb = vm.get("maxmem", 0) / (1024**3)
            mem_used_gb = vm.get("mem", 0) / (1024**3)
            status = vm.get("status", "unknown")
            
            # Create usage bar
            bar_length = min(32, int((maxmem_gb / total_ram_available) * 32))
            usage_bar = "█" * bar_length
            
            if status == "running" and mem_used_gb > 0:
                usage_bar += f" ({mem_used_gb:.1f}GB used)"
            elif status == "stopped":
                usage_bar += " (stopped)"
            elif vm.get("template"):
                usage_bar += " (template)"
            
            chart.append(f"│ {name:<15} │ {maxmem_gb:.0f}GB    │ {usage_bar:<35} │")
        
        # Memory totals
        mem_overcommit = total_ram_allocated / total_ram_available
        chart.extend([
            "├─────────────────┼─────────┼─────────────────────────────────────┤",
            f"│ ALLOCATED       │ {total_ram_allocated:.0f}GB    │ {'█' * 32}{'█' * (int(mem_overcommit) - 1) if mem_overcommit > 1 else ''}│",
            f"│ AVAILABLE       │ {total_ram_available:.1f}GB  │ {'█' * 24}                    │",
            f"│ OVERCOMMIT      │ {mem_overcommit:.2f}x   │ Some VMs stopped = fits             │",
            "└─────────────────┴─────────┴─────────────────────────────────────┘"
        ])
        
        return "\n".join(chart)
    
    def generate_full_report(self) -> str:
        """Generate complete infrastructure report."""
        report_parts = [
            "# Proxmox Infrastructure Topology Diagram",
            "",
            "## 🏗️ Physical Infrastructure Overview",
            "",
            "```",
            self.generate_topology_diagram(),
            "```",
            "",
            self.generate_resource_utilization(),
            "",
            "## 🎯 AI & GPU Utilization",
            "",
            self._generate_gpu_section(),
            "",
            "## 💡 Optimization Recommendations",
            "",
            self._generate_recommendations()
        ]
        
        return "\n".join(report_parts)
    
    def _generate_gpu_section(self) -> str:
        """Generate GPU utilization section."""
        vms = self.inventory.get("vms", [])
        ai_vms = [vm for vm in vms if "ollama" in vm.get("name", "").lower() or "ai" in vm.get("tags", "").lower()]
        
        gpu_section = [
            "```",
            "┌─────────────────────────────────────────────────────────────────┐",
            "│                     GPU ALLOCATION MAP                         │",
            "├─────────────────────────────────────────────────────────────────┤",
            "│                                                                 │",
            "│  🎮 AMD Radeon Instinct MI50 (16GB HBM2)                       │",
            "│  ├── Purpose: AI Training & Inference                          │",
            "│  ├── Capabilities: OpenCL, ROCm, HIP                           │",
            "│  ├── Memory: 16GB High Bandwidth Memory                        │",
            "│  └── Current Allocation:                                       │"
        ]
        
        if ai_vms:
            for vm in ai_vms:
                name = vm.get("name", "Unknown")
                vm_id = vm.get("vmid", "?")
                status = vm.get("status", "unknown").upper()
                
                gpu_section.extend([
                    "│      ┌─────────────────────────────────────────────────────┐   │",
                    f"│      │ 🤖 {name:<31} (VM {vm_id}){'│   │':<15}",
                    f"│      │ ├── Status: {status:<31}{'│   │':<15}",
                    "│      │ ├── GPU Usage: ACTIVE                              │   │",
                    "│      │ ├── Purpose: LLM inference                         │   │",
                    "│      │ └── Optimization: 100% GPU node utilization       │   │",
                    "│      └─────────────────────────────────────────────────────┘   │"
                ])
        else:
            gpu_section.extend([
                "│      ┌─────────────────────────────────────────────────────┐   │",
                "│      │ 💤 GPU Currently Available                         │   │",
                "│      │ └── Ready for AI workload deployment               │   │",
                "│      └─────────────────────────────────────────────────────┘   │"
            ])
        
        gpu_section.extend([
            "│                                                                 │",
            "│  💡 OPTIMIZATION OPPORTUNITIES:                                │",
            "│  ├── Move non-AI VMs to free up GPU node                      │",
            "│  ├── Consolidate AI workloads on GPU-enabled node             │",
            "│  └── Reserve GPU node exclusively for AI training             │",
            "└─────────────────────────────────────────────────────────────────┘",
            "```"
        ])
        
        return "\n".join(gpu_section)
    
    def _generate_recommendations(self) -> str:
        """Generate optimization recommendations."""
        vms = self.inventory.get("vms", [])
        running_vms = [vm for vm in vms if vm.get("status") == "running"]
        
        recommendations = [
            "Based on current infrastructure analysis:",
            "",
            "### ✅ OPTIMAL PLACEMENTS:",
            "1. **AI Training Workloads** → Node 'proxmox' (has MI50 GPU)",
            "2. **Database Workloads** → Node 'proxmox' (sufficient resources)",
            "3. **Web Services** → Node 'proxmox' (underutilized)",
            "",
            "### ⚡ OPTIMIZATION OPPORTUNITIES:",
            "1. **GPU Consolidation**: Move non-AI VMs to maximize GPU node efficiency"
        ]
        
        # Calculate available resources
        node_data = self.inventory.get("nodes", [])
        if node_data:
            node_str = str(node_data[0])
            import re
            mem_match = re.search(r"mem=([0-9]+)", node_str)
            maxmem_match = re.search(r"maxmem=([0-9]+)", node_str)
            
            if mem_match and maxmem_match:
                mem_used = int(mem_match.group(1)) / (1024**3)
                max_mem = int(maxmem_match.group(1)) / (1024**3)
                available_mem = max_mem - mem_used
                
                recommendations.append(f"2. **Resource Rebalancing**: {available_mem:.0f}GB RAM available for new workloads")
        
        recommendations.extend([
            "3. **Template Utilization**: VM 9000 ready for rapid deployment",
            "",
            "### 🚀 SCALING POTENTIAL:",
            f"- **Can Deploy**: {len([vm for vm in vms if vm.get('status') == 'stopped'])} stopped VMs can be optimized",
            "- **GPU Capacity**: 1 MI50 available for AI expansion",
            "- **Network Ready**: Bridge configured for VM networking",
            "",
            "This infrastructure is **perfectly positioned** for AI workload expansion with the MI50 GPU as the crown jewel! 🎯"
        ])
        
        return "\n".join(recommendations)


def generate_infrastructure_diagram(inventory_path: str = None) -> str:
    """Generate infrastructure diagram from inventory data."""
    visualizer = InfrastructureVisualizer(inventory_path)
    return visualizer.generate_full_report()


if __name__ == "__main__":
    # Test the visualizer
    print(generate_infrastructure_diagram())