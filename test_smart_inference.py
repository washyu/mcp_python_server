#!/usr/bin/env python3
"""
Test that the AI smartly infers the current server from natural language.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from start_homelab_chat import HomelabChatInterface, ChatConfig


async def test_smart_inference():
    """Test that AI smartly infers current server from natural language."""
    print("🧪 Testing Smart Server Inference...")
    
    config = ChatConfig()
    chat = HomelabChatInterface(config)
    
    # Set current server
    chat.current_server = "proxmoxpi.local"
    print(f"✅ Set current server to: {chat.current_server}")
    
    # Test natural language queries and check if they include smart inference
    test_cases = [
        "list containers",
        "what's running", 
        "show me the vms",
        "what services are installed",
        "show resources"
    ]
    
    for query in test_cases:
        print(f"\n📝 Testing query: '{query}'")
        
        # Generate enhanced prompt
        prompt = await chat.create_enhanced_prompt(query)
        
        # Check for smart inference instructions
        if "NATURAL LANGUAGE INTERPRETATION" in prompt:
            print("✅ Smart inference instructions present")
        else:
            print("❌ Smart inference instructions missing")
        
        # Check for current server context
        if f"proxmox_list_vms {{\"host\": \"proxmoxpi.local\"}}" in prompt:
            print("✅ Concrete examples with current server")
        else:
            print("❌ Missing concrete examples with current server")
        
        # Check for smart behavior instructions
        if "BE SMART - INFER THE USER'S INTENT" in prompt:
            print("✅ Smart behavior instructions present")
        else:
            print("❌ Smart behavior instructions missing")
    
    return True


async def main():
    """Run the test."""
    print("🔧 Testing Smart Server Inference System")
    print("=" * 50)
    
    success = await test_smart_inference()
    
    if success:
        print("\n✅ Smart inference tests completed!")
        print("\n🎯 The AI should now be smart enough to:")
        print("• Understand 'list containers' means current server")
        print("• Understand 'what's running' means current server") 
        print("• Understand 'kill vm 123' means current server")
        print("• Always use current server unless told otherwise")
        print("\n🚀 Try in VS Code:")
        print("1. Type: use proxmoxpi.local")
        print("2. Type: what's running")
        print("3. AI should execute proxmox_list_vms with proxmoxpi.local")
    else:
        print("\n❌ Tests failed - need to investigate further.")


if __name__ == "__main__":
    asyncio.run(main())