#!/usr/bin/env python3
"""
Compare AI-powered filtering vs explicit filtering approaches.
"""

import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# Sample VM data from our actual inventory
SAMPLE_VMS = [
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

def simulate_ai_filtering(user_query: str, vm_data: list) -> str:
    """
    Simulate what an AI would do with raw JSON data.
    This is a mock since we don't want to call actual AI for testing.
    """
    
    # Create a prompt that an AI would receive
    ai_prompt = f"""
User Query: "{user_query}"

VM Data:
{json.dumps(vm_data, indent=2)}

Based on the user's query, filter and format the VMs appropriately. 
Show only VMs that match the criteria mentioned in the query.
"""
    
    # Simulate AI analysis (this would be actual AI processing)
    query_lower = user_query.lower()
    
    # Mock AI logic for common patterns
    if "running" in query_lower:
        filtered = [vm for vm in vm_data if vm["status"] == "running"]
    elif "mysql" in query_lower:
        filtered = [vm for vm in vm_data if "mysql" in vm.get("name", "").lower() or "mysql" in vm.get("tags", "").lower()]
    elif "8gb" in query_lower or "8 gb" in query_lower:
        filtered = [vm for vm in vm_data if vm["maxmem"] >= 8 * 1024 * 1024 * 1024]
    elif "vm 203" in query_lower:
        filtered = [vm for vm in vm_data if vm["vmid"] == 203]
    else:
        filtered = vm_data  # Show all if unsure
    
    return f"AI would filter to: {len(filtered)} VMs - {[vm['name'] for vm in filtered]}"

def explicit_filtering(user_query: str, vm_data: list) -> str:
    """
    Use our explicit filtering approach.
    """
    from src.agents.websocket_agent import WebSocketAIAgent
    from src.tools.proxmox_discovery import ProxmoxDiscoveryTools
    
    agent = WebSocketAIAgent()
    discovery = ProxmoxDiscoveryTools()
    
    # Parse filters using our system
    filters = agent._parse_vm_filters(user_query)
    
    # Apply filters like our system does
    filtered = vm_data
    if filters.get("status"):
        filtered = [vm for vm in filtered if vm.get("status") == filters["status"]]
    if filters.get("id"):
        filtered = [vm for vm in filtered if vm.get("vmid") == filters["id"]]
    if filters.get("name"):
        filtered = [vm for vm in filtered if filters["name"] in vm.get("name", "").lower()]
    if filters.get("min_memory"):
        min_bytes = filters["min_memory"] * 1024 * 1024
        filtered = [vm for vm in filtered if vm.get("maxmem", 0) >= min_bytes]
    if filters.get("os"):
        filtered = [vm for vm in filtered if discovery._matches_os_filter(vm, filters["os"])]
    
    return f"Explicit filters {filters} → {len(filtered)} VMs - {[vm['name'] for vm in filtered]}"

def compare_approaches():
    """Compare AI vs explicit filtering for various queries."""
    
    test_queries = [
        "running vms",
        "mysql servers", 
        "vm 203",
        "servers with 8gb memory",
        "production servers",
        "windows vms",  # None exist
        "microsoft bob instances",  # Nonsensical
    ]
    
    print("🔍 AI vs Explicit Filtering Comparison\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"{i}. Query: '{query}'")
        
        # AI approach (simulated)
        ai_result = simulate_ai_filtering(query, SAMPLE_VMS)
        print(f"   🤖 AI Approach: {ai_result}")
        
        # Explicit approach
        explicit_result = explicit_filtering(query, SAMPLE_VMS)
        print(f"   🛠️  Explicit:    {explicit_result}")
        
        print()

def show_token_usage_comparison():
    """Show the token usage difference."""
    
    print("💰 Token Usage Comparison\n")
    
    # AI approach - would send full JSON every time
    full_json = json.dumps(SAMPLE_VMS, indent=2)
    ai_tokens = len(full_json.split())  # Rough token estimate
    
    # Explicit approach - only sends results
    explicit_tokens = len("ollama-server".split())  # Typical result
    
    print(f"🤖 AI Approach per query:")
    print(f"   Input: {ai_tokens} tokens (full VM JSON)")
    print(f"   Output: ~50 tokens (filtered response)")
    print(f"   Total: ~{ai_tokens + 50} tokens per query")
    print()
    
    print(f"🛠️  Explicit Approach per query:")
    print(f"   Input: ~10 tokens (filter parsing)")
    print(f"   Output: {explicit_tokens} tokens (result names)")
    print(f"   Total: ~{10 + explicit_tokens} tokens per query")
    print()
    
    print(f"💡 Token Savings: {((ai_tokens + 50) / (10 + explicit_tokens)):.1f}x more efficient")

if __name__ == "__main__":
    compare_approaches()
    show_token_usage_comparison()