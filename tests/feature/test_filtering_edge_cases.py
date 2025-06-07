#!/usr/bin/env python3
"""
Test edge cases for VM filtering functionality.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.agents.websocket_agent import WebSocketAIAgent

def test_edge_case_filters():
    """Test edge case filter parsing."""
    agent = WebSocketAIAgent()
    
    # Test cases with expected results
    test_cases = [
        # Status edge cases
        ("paused vms", {"status": "paused"}),
        ("suspended machines", {"status": "paused"}),
        
        # ID edge cases  
        ("vm #203", {"id": 203}),
        ("server 999", {"id": 999}), 
        ("vm -1", {}),  # Should be filtered out
        ("vm 999999", {}),  # Should be filtered out
        
        # Memory edge cases
        ("vms with 1.5gb", {"min_memory": 1536}),  # 1.5 * 1024
        ("servers with 4096mb", {"min_memory": 4096}),
        ("exactly 8gb memory", {"min_memory": 8192}),
        
        # CPU edge cases
        ("dual core servers", {"min_cpu": 2}),
        ("quad core machines", {"min_cpu": 4}),
        ("single core vms", {"min_cpu": 1}),
        ("machines with 0.5 cores", {}),  # Should be filtered out
        
        # Name edge cases
        ("production servers", {"name": "production"}),
        ("dev machines", {"name": "dev"}),
        ("mysql-database servers", {"name": "mysql"}),
        
        # OS edge cases
        ("ubuntu 22.04 servers", {"os": "ubuntu 22.04"}),
        ("windows server 2022", {"os": "windows server 2022"}),
        
        # Complex queries
        ("running ubuntu vms with 8gb", {"status": "running", "os": "ubuntu", "min_memory": 8192}),
        ("production mysql servers with 4 cores", {"name": "mysql", "min_cpu": 4}),
        
        # Real VM test cases (from our inventory)
        ("vm 203", {"id": 203}),  # ollama-server
        ("vm 998", {"id": 998}),  # ai-mysql-test
        ("mysql test servers", {"name": "mysql"}),  # Should match ai-mysql-test
    ]
    
    print("🧪 Testing Edge Case Filters\n")
    
    for i, (query, expected) in enumerate(test_cases, 1):
        result = agent._parse_vm_filters(query)
        
        # Check if all expected keys are present with correct values
        passed = True
        for key, value in expected.items():
            if key not in result or result[key] != value:
                passed = False
                break
        
        # Also check no unexpected extra keys (allow empty expected)
        if expected and len(result) != len(expected):
            passed = False
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{i:2d}. {status} | '{query}' -> {result}")
        if not passed:
            print(f"    Expected: {expected}")
    
    print(f"\n📊 Summary: Testing completed for {len(test_cases)} edge cases")

def test_real_data_filtering():
    """Test filters against real Proxmox data."""
    print("\n🔍 Testing Against Real Data\n")
    
    # Sample VMs from our actual inventory
    test_vms = [
        {
            "vmid": 203,
            "name": "ollama-server", 
            "status": "running",
            "maxmem": 17179869184,  # 16GB
            "cpus": 8,
            "node": "proxmox"
        },
        {
            "vmid": 998,
            "name": "ai-mysql-test",
            "status": "stopped", 
            "maxmem": 4294967296,  # 4GB
            "cpus": 2,
            "tags": "ai-created;mcp-managed;mysql-database",
            "node": "proxmox"
        },
        {
            "vmid": 999,
            "name": "production-database-server",
            "status": "running",
            "maxmem": 34359738368,  # 32GB
            "cpus": 4,
            "tags": "ai-created;mcp-managed;pipeline-test;purpose--PURPOSE",
            "node": "proxmox"
        }
    ]
    
    # Import the OS matching function
    from src.tools.proxmox_discovery import ProxmoxDiscoveryTools
    discovery = ProxmoxDiscoveryTools()
    
    # Test specific queries
    test_queries = [
        ("vm 203", "Should find ollama-server"),
        ("mysql servers", "Should find ai-mysql-test"),
        ("production servers", "Should find production-database-server"),
        ("running vms with 8gb", "Should find ollama-server and production-database-server"),
        ("stopped mysql vms", "Should find ai-mysql-test"),
        ("servers with 4 cores", "Should find production-database-server")
    ]
    
    agent = WebSocketAIAgent()
    
    for query, description in test_queries:
        filters = agent._parse_vm_filters(query)
        
        # Apply filters manually to test VMs
        matches = []
        for vm in test_vms:
            match = True
            
            # Apply each filter
            if "status" in filters and vm.get("status") != filters["status"]:
                match = False
            if "id" in filters and vm.get("vmid") != filters["id"]:
                match = False
            if "name" in filters and filters["name"] not in vm.get("name", "").lower():
                match = False
            if "min_memory" in filters:
                min_bytes = filters["min_memory"] * 1024 * 1024
                if vm.get("maxmem", 0) < min_bytes:
                    match = False
            if "min_cpu" in filters and vm.get("cpus", 0) < filters["min_cpu"]:
                match = False
            if "os" in filters:
                if not discovery._matches_os_filter(vm, filters["os"]):
                    match = False
            
            if match:
                matches.append(vm["name"])
        
        print(f"Query: '{query}'")
        print(f"Filters: {filters}")
        print(f"Matches: {matches if matches else 'None'}")
        print(f"Expected: {description}")
        print()


if __name__ == "__main__":
    test_edge_case_filters()
    test_real_data_filtering()