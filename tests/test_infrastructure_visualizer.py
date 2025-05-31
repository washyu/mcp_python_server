#!/usr/bin/env python3
"""
Test infrastructure visualization and diagram generation functionality.
"""

import pytest
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.append(str(Path(__file__).parent.parent))

from src.tools.infrastructure_visualizer import InfrastructureVisualizer


@pytest.fixture
def sample_inventory_data():
    """Sample inventory data for testing."""
    return {
        "nodes": [
            "ProxmoxNode(node='proxmox', status='online', cpu=0.047, maxcpu=12, mem=18409906176, maxmem=66677018624, disk=6435983360, maxdisk=100861726720, uptime=15994, level='', id='node/proxmox')"
        ],
        "vms": [
            {
                "vmid": 203,
                "name": "ollama-server",
                "status": "running",
                "cpus": 8,
                "maxmem": 17179869184,  # 16GB
                "maxdisk": 107374182400,  # 100GB
                "mem": 12396097234,  # 11.5GB used
                "cpu": 0.02,
                "node": "proxmox",
                "tags": "ai-training"
            },
            {
                "vmid": 998,
                "name": "ai-mysql-test",
                "status": "stopped",
                "cpus": 2,
                "maxmem": 4294967296,  # 4GB
                "maxdisk": 10737418240,  # 10GB
                "mem": 0,
                "cpu": 0,
                "node": "proxmox",
                "tags": "ai-created;mcp-managed;mysql-database"
            },
            {
                "vmid": 9000,
                "name": "ubuntu-cloud-template",
                "status": "stopped",
                "cpus": 1,
                "maxmem": 2147483648,  # 2GB
                "maxdisk": 2361393152,  # 2.2GB
                "template": 1,
                "node": "proxmox"
            }
        ],
        "storage": [
            {
                "storage": "local",
                "type": "dir",
                "path": "/var/lib/vz",
                "content": "backup,iso,vztmpl"
            },
            {
                "storage": "local-lvm", 
                "type": "lvmthin",
                "content": "images,rootdir"
            }
        ],
        "networks": [
            {
                "iface": "vmbr0",
                "type": "bridge",
                "address": "192.168.10.200",
                "netmask": "24",
                "gateway": "192.168.10.1"
            },
            {
                "iface": "eth1",
                "type": "eth",
                "method": "manual"
            }
        ]
    }


@pytest.fixture
def temp_inventory_file(sample_inventory_data):
    """Create temporary inventory file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_inventory_data, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink()


class TestInfrastructureVisualizer:
    """Test the main visualizer class."""
    
    def test_visualizer_initialization(self, temp_inventory_file):
        """Test visualizer initialization with inventory file."""
        viz = InfrastructureVisualizer(temp_inventory_file)
        
        assert viz.inventory_path == temp_inventory_file
        assert viz.inventory is not None
        assert "nodes" in viz.inventory
        assert "vms" in viz.inventory
    
    def test_visualizer_initialization_missing_file(self):
        """Test visualizer initialization with missing file."""
        viz = InfrastructureVisualizer("nonexistent.json")
        
        # Should create empty inventory
        assert viz.inventory == {"nodes": [], "vms": [], "storage": [], "networks": [], "templates": []}


class TestNodeDataParsing:
    """Test node data parsing from string representation."""
    
    def test_parse_node_data_valid(self, temp_inventory_file):
        """Test parsing valid node data string."""
        viz = InfrastructureVisualizer(temp_inventory_file)
        
        node_str = "ProxmoxNode(node='proxmox', status='online', cpu=0.047, maxcpu=12, mem=18409906176, maxmem=66677018624, uptime=15994)"
        node_info = viz._parse_node_data(node_str)
        
        assert node_info["name"] == "proxmox"
        assert node_info["status"] == "online"
        assert "12 cores" in node_info["cpu_spec"]
        assert "4.7%" in node_info["cpu_spec"]
        assert "62.1GB total" in node_info["ram_spec"]
        assert "17.1GB used" in node_info["ram_spec"]
        assert "4.4 hours" in node_info["uptime"]
    
    def test_parse_node_data_none(self, temp_inventory_file):
        """Test parsing None node data."""
        viz = InfrastructureVisualizer(temp_inventory_file)
        
        node_info = viz._parse_node_data(None)
        
        assert node_info["name"] == "unknown"
        assert node_info["status"] == "unknown"
        assert "unknown" in node_info["cpu_spec"]


class TestVMCategorization:
    """Test VM categorization logic."""
    
    def test_categorize_ai_vm(self, temp_inventory_file):
        """Test AI VM categorization."""
        viz = InfrastructureVisualizer(temp_inventory_file)
        
        category = viz._categorize_vm("ollama-server", "ai-training")
        
        assert category["emoji"] == "🤖"
        assert category["category"] == "AI TRAINING"
        assert "LLM inference" in category["description"]
    
    def test_categorize_database_vm(self, temp_inventory_file):
        """Test database VM categorization."""
        viz = InfrastructureVisualizer(temp_inventory_file)
        
        category = viz._categorize_vm("mysql-server", "mysql-database")
        
        assert category["emoji"] == "💾"
        assert category["category"] == "DATABASE"
        assert "Database server" in category["description"]
    
    def test_categorize_template_vm(self, temp_inventory_file):
        """Test template VM categorization."""
        viz = InfrastructureVisualizer(temp_inventory_file)
        
        category = viz._categorize_vm("ubuntu-cloud-template", "")
        
        assert category["emoji"] == "📦"
        assert category["category"] == "TEMPLATE"
        assert "VM template" in category["description"]
    
    def test_categorize_development_vm(self, temp_inventory_file):
        """Test development VM categorization.""" 
        viz = InfrastructureVisualizer(temp_inventory_file)
        
        category = viz._categorize_vm("dev-environment", "")
        
        assert category["emoji"] == "🔧"
        assert category["category"] == "DEVELOPMENT"
    
    def test_categorize_generic_vm(self, temp_inventory_file):
        """Test generic VM categorization."""
        viz = InfrastructureVisualizer(temp_inventory_file)
        
        category = viz._categorize_vm("random-server", "")
        
        assert category["emoji"] == "⚙️"
        assert category["category"] == "GENERAL"


class TestTopologyDiagramGeneration:
    """Test topology diagram generation."""
    
    def test_generate_topology_diagram(self, temp_inventory_file):
        """Test basic topology diagram generation."""
        viz = InfrastructureVisualizer(temp_inventory_file)
        
        diagram = viz.generate_topology_diagram()
        
        assert isinstance(diagram, str)
        assert len(diagram) > 100  # Should be substantial
        
        # Check for expected components
        assert "PROXMOX CLUSTER" in diagram
        assert "192.168.10.200" in diagram
        assert "NODE: proxmox" in diagram
        assert "VIRTUAL MACHINES" in diagram
        assert "ollama-server" in diagram
        assert "🤖 AI TRAINING" in diagram
    
    def test_topology_diagram_structure(self, temp_inventory_file):
        """Test topology diagram structure and formatting."""
        viz = InfrastructureVisualizer(temp_inventory_file)
        
        diagram = viz.generate_topology_diagram()
        lines = diagram.split('\n')
        
        # Check for proper ASCII art formatting
        assert any("┌─" in line for line in lines)  # Top borders
        assert any("└─" in line for line in lines)  # Bottom borders
        assert any("│" in line for line in lines)   # Vertical borders
        
        # Check for hardware specs section
        hardware_section = any("HARDWARE SPECIFICATIONS" in line for line in lines)
        assert hardware_section
        
        # Check for VM section
        vm_section = any("RUNNING VMs" in line for line in lines)
        assert vm_section
    
    def test_vm_box_creation(self, temp_inventory_file):
        """Test VM box creation."""
        viz = InfrastructureVisualizer(temp_inventory_file)
        
        sample_vm = {
            "vmid": 203,
            "name": "ollama-server",
            "cpus": 8,
            "maxmem": 17179869184,
            "mem": 12396097234,
            "cpu": 0.02,
            "status": "running"
        }
        
        vm_box = viz._create_vm_box(sample_vm, "running")
        
        assert isinstance(vm_box, list)
        assert len(vm_box) > 5  # Should have multiple lines
        
        box_text = '\n'.join(vm_box)
        assert "VM 203: ollama-server" in box_text
        assert "CPU: 8 cores" in box_text
        assert "RAM: 16GB" in box_text
        assert "🤖 AI TRAINING" in box_text


class TestResourceUtilizationGeneration:
    """Test resource utilization chart generation."""
    
    def test_generate_resource_utilization(self, temp_inventory_file):
        """Test resource utilization chart generation."""
        viz = InfrastructureVisualizer(temp_inventory_file)
        
        chart = viz.generate_resource_utilization()
        
        assert isinstance(chart, str)
        assert "Resource Utilization Analysis" in chart
        assert "CPU Distribution" in chart
        assert "Memory Distribution" in chart
        
        # Check for table formatting
        assert "┌─" in chart  # Table borders
        assert "├─" in chart  # Table separators
        assert "└─" in chart  # Table bottom
        
        # Check for VM entries
        assert "ollama-server" in chart
        assert "ai-mysql-test" in chart
    
    def test_cpu_utilization_bars(self, temp_inventory_file):
        """Test CPU utilization bar generation."""
        viz = InfrastructureVisualizer(temp_inventory_file)
        
        chart = viz.generate_resource_utilization()
        
        # Should show usage bars with █ characters
        assert "█" in chart
        
        # Should show overcommit calculations
        assert "OVERCOMMIT" in chart
        assert "ALLOCATED" in chart
        assert "AVAILABLE" in chart
    
    def test_memory_utilization_display(self, temp_inventory_file):
        """Test memory utilization display."""
        viz = InfrastructureVisualizer(temp_inventory_file)
        
        chart = viz.generate_resource_utilization()
        
        # Should show memory in GB
        assert "GB" in chart
        assert "Memory Distribution" in chart
        
        # Should include running VM memory usage
        assert "used" in chart


class TestFullReportGeneration:
    """Test full infrastructure report generation."""
    
    def test_generate_full_report(self, temp_inventory_file):
        """Test complete infrastructure report generation."""
        viz = InfrastructureVisualizer(temp_inventory_file)
        
        report = viz.generate_full_report()
        
        assert isinstance(report, str)
        assert len(report) > 1000  # Should be comprehensive
        
        # Check all major sections are present
        assert "Infrastructure Topology Diagram" in report
        assert "Resource Utilization Analysis" in report
        assert "GPU Utilization" in report
        assert "Optimization Recommendations" in report
    
    def test_gpu_section_generation(self, temp_inventory_file):
        """Test GPU section generation."""
        viz = InfrastructureVisualizer(temp_inventory_file)
        
        gpu_section = viz._generate_gpu_section()
        
        assert "GPU ALLOCATION MAP" in gpu_section
        assert "AMD Radeon Instinct MI50" in gpu_section
        assert "AI Training & Inference" in gpu_section
        assert "🎮" in gpu_section  # GPU emoji
    
    def test_recommendations_generation(self, temp_inventory_file):
        """Test recommendations section generation."""
        viz = InfrastructureVisualizer(temp_inventory_file)
        
        recommendations = viz._generate_recommendations()
        
        assert "OPTIMAL PLACEMENTS" in recommendations
        assert "OPTIMIZATION OPPORTUNITIES" in recommendations
        assert "SCALING POTENTIAL" in recommendations
        assert "MI50 GPU" in recommendations


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_inventory(self):
        """Test visualization with empty inventory."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"nodes": [], "vms": [], "storage": [], "networks": []}, f)
            temp_path = f.name
        
        try:
            viz = InfrastructureVisualizer(temp_path)
            diagram = viz.generate_topology_diagram()
            
            # Should handle empty data gracefully
            assert isinstance(diagram, str)
            assert "PROXMOX CLUSTER" in diagram
        finally:
            Path(temp_path).unlink()
    
    def test_malformed_node_data(self, temp_inventory_file):
        """Test handling of malformed node data."""
        viz = InfrastructureVisualizer(temp_inventory_file)
        
        # Test with malformed string
        node_info = viz._parse_node_data("invalid_node_string")
        
        assert node_info["name"] == "unknown"
        assert "unknown" in node_info["cpu_spec"]
    
    def test_missing_vm_fields(self, temp_inventory_file):
        """Test handling of VMs with missing fields."""
        viz = InfrastructureVisualizer(temp_inventory_file)
        
        incomplete_vm = {"vmid": 123, "name": "test"}  # Missing many fields
        
        vm_box = viz._create_vm_box(incomplete_vm, "running")
        
        # Should handle gracefully without crashing
        assert isinstance(vm_box, list)
        assert len(vm_box) > 0


class TestFunctionalIntegration:
    """Test integration with the main generate function."""
    
    def test_generate_infrastructure_diagram_function(self, temp_inventory_file):
        """Test the main generate function."""
        from src.tools.infrastructure_visualizer import generate_infrastructure_diagram
        
        diagram = generate_infrastructure_diagram(temp_inventory_file)
        
        assert isinstance(diagram, str)
        assert "Infrastructure Topology Diagram" in diagram
        assert "ollama-server" in diagram
        assert "🤖" in diagram  # AI emoji
    
    def test_generate_with_default_path(self):
        """Test generate function with default path."""
        from src.tools.infrastructure_visualizer import generate_infrastructure_diagram
        
        # Should not crash even with missing default file
        diagram = generate_infrastructure_diagram()
        
        assert isinstance(diagram, str)
        # May have empty data but should still generate structure


if __name__ == "__main__":
    pytest.main([__file__, "-v"])