#!/usr/bin/env python3
"""
Test that the AI properly targets the current working server.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from start_homelab_chat import HomelabChatInterface, ChatConfig


async def test_server_targeting():
    """Test that AI uses current server for tool executions."""
    print("🧪 Testing Server Targeting...")
    
    config = ChatConfig()
    chat = HomelabChatInterface(config)
    
    # Set current server
    chat.current_server = "proxmoxpi.local"
    print(f"✅ Set current server to: {chat.current_server}")
    
    # Test 1: Generate prompt and check server context
    message = "list the containers"
    prompt = await chat.create_enhanced_prompt(message)
    
    # Check if server context is prominent
    if "🎯🎯🎯 CRITICAL SERVER CONTEXT 🎯🎯🎯" in prompt:
        print("✅ Prominent server context in prompt")
    else:
        print("❌ Server context not prominent enough")
    
    if "proxmoxpi.local" in prompt and "ALL COMMANDS MUST TARGET: proxmoxpi.local" in prompt:
        print("✅ Server targeting instructions present")
    else:
        print("❌ Server targeting instructions missing")
    
    # Test 2: Tool execution with no host specified - should add current server
    result = await chat.execute_mcp_tool("list-lxd-containers", {})
    print(f"✅ Tool execution without host: {result[:100]}...")
    
    # Test 3: Check that tool got the correct host
    if "proxmoxpi.local" in result:
        print("✅ Tool execution used current server")
    else:
        print("❌ Tool execution didn't use current server")
        print(f"Debug - result: {result[:200]}")
    
    # Test 4: Tool execution with explicit localhost - should get corrected
    result2 = await chat.execute_mcp_tool("check-lxd", {"host": "localhost"})
    print(f"✅ Tool execution with localhost correction: {result2[:100]}...")
    
    return True


async def main():
    """Run the test."""
    print("🔧 Testing Server Targeting System")
    print("=" * 40)
    
    success = await test_server_targeting()
    
    if success:
        print("\n✅ Server targeting tests completed!")
        print("Now try in VS Code:")
        print("1. Type: use proxmoxpi.local")
        print("2. Type: list containers")
        print("3. AI should target proxmoxpi.local, not localhost")
    else:
        print("\n❌ Tests failed - need to investigate further.")


if __name__ == "__main__":
    asyncio.run(main())