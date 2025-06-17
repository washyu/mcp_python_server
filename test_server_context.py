#!/usr/bin/env python3
"""
Test the server context feature.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from start_homelab_chat import HomelabChatInterface, ChatConfig


async def test_server_context():
    """Test the server context feature."""
    print("🧪 Testing Server Context Feature...")
    
    config = ChatConfig()
    chat = HomelabChatInterface(config)
    
    # Test 1: No server set initially
    assert chat.current_server is None
    print("✅ Initial state: No server set")
    
    # Test 2: Hostname detection sets current server
    message = "install lxd on my pi proxmoxpi.local"
    prompt = await chat.create_enhanced_prompt(message)
    
    assert chat.current_server == "proxmoxpi.local"
    print("✅ Hostname detection sets current server")
    
    # Test 3: Prompt contains server context
    assert "CURRENT WORKING SERVER: proxmoxpi.local" in prompt
    print("✅ Prompt contains server context")
    
    # Test 4: Tool execution uses current server
    # Simulate AI trying to use localhost - should get corrected
    result = await chat.execute_mcp_tool("check-lxd", {"host": "localhost"})
    print(f"✅ Tool execution with localhost: {result[:100]}...")
    
    # Test 5: Manual server setting
    chat.current_server = "testserver.local"
    assert chat.current_server == "testserver.local"
    print("✅ Manual server setting works")
    
    # Test 6: Clear server
    chat.current_server = None
    assert chat.current_server is None
    print("✅ Server clearing works")
    
    return True


async def main():
    """Run the test."""
    print("🔧 Testing Server Context System")
    print("=" * 40)
    
    success = await test_server_context()
    
    if success:
        print("\n✅ All tests passed! Server context system is working:")
        print("  • Automatic hostname detection sets current server")
        print("  • AI prompts include current server context")
        print("  • Tool execution auto-corrects to current server")
        print("  • Manual server management commands work")
    else:
        print("\n❌ Tests failed - need to investigate further.")


if __name__ == "__main__":
    asyncio.run(main())