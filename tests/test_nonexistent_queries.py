#!/usr/bin/env python3
"""
Test queries for non-existent or unusual OS types and services.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.agents.websocket_agent import WebSocketAIAgent
from src.tools.proxmox_discovery import ProxmoxDiscoveryTools

def test_nonexistent_queries():
    """Test queries for systems that don't exist in our environment."""
    agent = WebSocketAIAgent()
    discovery = ProxmoxDiscoveryTools()
    
    # Real VMs from our inventory for testing
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
        }
    ]
    
    # Test queries for non-existent things
    nonexistent_queries = [
        # Obsolete/unusual OS
        ("windows 3.11 servers", "Ancient Windows version"),
        ("microsoft bob instances", "Obscure Microsoft product"),
        ("dos 6.22 machines", "Very old DOS version"),
        ("os/2 warp servers", "IBM OS/2"),
        ("amiga workbench vms", "Amiga OS"),
        ("commodore 64 instances", "8-bit computer"),
        
        # Modern but unlikely in homelab
        ("mainframe servers", "Enterprise mainframes"),
        ("supercomputer instances", "HPC systems"),
        ("quantum computers", "Quantum systems"),
        
        # Fictional/joke OS
        ("skynet servers", "Terminator reference"),
        ("hal 9000 instances", "2001 Space Odyssey"),
        ("jarvis systems", "Iron Man AI"),
        
        # Services that don't exist in our lab
        ("oracle database servers", "Enterprise database"),
        ("sap instances", "Enterprise ERP"),
        ("lotus notes servers", "Old collaboration software"),
        ("netware servers", "Novell NetWare"),
        
        # Typos and variations
        ("linus servers", "Misspelled Linux"),
        ("windwos servers", "Misspelled Windows"),
        ("ubunut machines", "Misspelled Ubuntu"),
        
        # Completely nonsensical
        ("toaster servers", "Kitchen appliances"),
        ("refrigerator instances", "More appliances"),
        ("bicycle computers", "Non-computer systems")
    ]
    
    print("🔍 Testing Non-Existent and Unusual Queries\n")
    
    for i, (query, description) in enumerate(nonexistent_queries, 1):
        # Parse the filters
        filters = agent._parse_vm_filters(query)
        
        # Apply filters to our test VMs
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
        
        # Show results
        result_text = f"{'No matches' if not matches else f'Matches: {matches}'}"
        status = "✅ GOOD" if not matches else "⚠️  UNEXPECTED"
        
        print(f"{i:2d}. {status} | '{query}'")
        print(f"    Filters: {filters}")
        print(f"    Result: {result_text}")
        print(f"    Expected: {description} - should find nothing")
        print()

def test_graceful_handling():
    """Test how the system handles edge cases gracefully."""
    print("🛡️ Testing Graceful Error Handling\n")
    
    agent = WebSocketAIAgent()
    
    edge_cases = [
        # Empty/minimal queries
        ("", "Empty query"),
        ("vms", "Generic term only"),
        ("servers", "Generic term only"),
        ("machines", "Generic term only"),
        
        # Malformed queries
        ("vms with gb memory", "Missing memory amount"),
        ("servers with cores", "Missing CPU count"),
        ("running with", "Incomplete filter"),
        ("id", "Missing ID number"),
        
        # Conflicting requirements
        ("running stopped vms", "Contradictory status"),
        ("windows linux servers", "Contradictory OS"),
        ("vm 203 vm 998", "Multiple IDs"),
        
        # Extreme values
        ("vms with 999gb memory", "Excessive memory"),
        ("servers with 100 cores", "Excessive CPU"),
        ("vm 99999999", "Huge VM ID"),
        
        # Special characters and formatting
        ("vm's with memory", "Apostrophe"),
        ("servers (production)", "Parentheses"),
        ("vms/machines", "Slash separator"),
        ("servers & machines", "Ampersand")
    ]
    
    for i, (query, description) in enumerate(edge_cases, 1):
        try:
            filters = agent._parse_vm_filters(query)
            status = "✅ HANDLED"
            result = f"Parsed: {filters}"
        except Exception as e:
            status = "❌ ERROR"
            result = f"Exception: {e}"
        
        print(f"{i:2d}. {status} | '{query}'")
        print(f"    {result}")
        print(f"    Test: {description}")
        print()

if __name__ == "__main__":
    test_nonexistent_queries()
    test_graceful_handling()