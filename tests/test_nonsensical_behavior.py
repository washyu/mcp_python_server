#!/usr/bin/env python3
"""
Test the improved behavior for nonsensical queries.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.agents.websocket_agent import WebSocketAIAgent
from rich.console import Console

def test_nonsensical_detection():
    """Test that nonsensical queries are detected and handled gracefully."""
    agent = WebSocketAIAgent()
    console = Console()
    
    test_cases = [
        # Should trigger helpful tips
        ("microsoft bob instances", True),
        ("skynet servers", True), 
        ("hal 9000 machines", True),
        ("toaster computers", True),
        ("amiga workbench vms", True),
        ("dos 6.22 servers", True),
        ("mainframe instances", True),
        
        # Should NOT trigger tips (legitimate queries)
        ("mysql servers", False),
        ("ubuntu machines", False),
        ("windows vms", False),
        ("running servers", False),
        ("vm 203", False),
        ("list vms", False),
        ("production servers", False),
    ]
    
    print("🤖 Testing Nonsensical Query Detection\n")
    
    for i, (query, should_trigger_tip) in enumerate(test_cases, 1):
        filters = agent._parse_vm_filters(query)
        
        # Check if query would trigger the helpful tip
        will_trigger = (
            not filters and 
            any(term in query.lower() for term in [
                "bob", "skynet", "hal", "jarvis", "toaster", "refrigerator", 
                "bicycle", "amiga", "commodore", "dos", "os/2", "mainframe"
            ])
        )
        
        status = "✅ CORRECT" if will_trigger == should_trigger_tip else "❌ WRONG"
        behavior = "Shows tip" if will_trigger else "Normal search"
        
        print(f"{i:2d}. {status} | '{query}'")
        print(f"    Behavior: {behavior}")
        print(f"    Expected: {'Should show tip' if should_trigger_tip else 'Should search normally'}")
        print(f"    Filters: {filters}")
        print()

def demonstrate_user_experience():
    """Show what the user experience looks like."""
    print("👤 User Experience Examples\n")
    
    examples = [
        ("Query: 'windows 3.11 servers'", "windows 3.11 servers"),
        ("Query: 'microsoft bob instances'", "microsoft bob instances"),
        ("Query: 'mysql servers'", "mysql servers"),
    ]
    
    agent = WebSocketAIAgent()
    
    for title, query in examples:
        print(f"📝 {title}")
        filters = agent._parse_vm_filters(query)
        
        # Simulate the logic
        will_show_tip = (
            not filters and 
            any(term in query.lower() for term in [
                "bob", "skynet", "hal", "jarvis", "toaster", "refrigerator", 
                "bicycle", "amiga", "commodore", "dos", "os/2", "mainframe"
            ])
        )
        
        if will_show_tip:
            print("💡 Response: Tip about system not being in homelab")
        else:
            if filters:
                print(f"🔍 Response: Searches with filters: {filters}")
            else:
                print("📋 Response: Lists all VMs (no filters)")
        print()

if __name__ == "__main__":
    test_nonsensical_detection()
    demonstrate_user_experience()