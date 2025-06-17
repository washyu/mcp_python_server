#!/usr/bin/env python3
"""
Test script to verify MCP tool execution works correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.tools.homelab_tools import HOMELAB_TOOLS, handle_homelab_tool
from src.tools.agent_homelab_tools import AGENT_HOMELAB_TOOLS, handle_agent_homelab_tool
from src.tools.lxd_tools import LXD_TOOLS, handle_lxd_tool
from src.tools.proxmox_discovery import PROXMOX_TOOLS, handle_proxmox_tool

# Combine all tools
ALL_TOOLS = AGENT_HOMELAB_TOOLS + LXD_TOOLS + HOMELAB_TOOLS + PROXMOX_TOOLS


async def test_tool_discovery():
    """Test discovering available MCP tools."""
    print("🔍 Testing MCP Tool Discovery...")
    print(f"✅ Found {len(ALL_TOOLS)} MCP tools:")
    
    for tool in ALL_TOOLS:
        print(f"  • {tool.name}: {tool.description}")
    
    print()


async def test_tool_execution():
    """Test executing a simple MCP tool."""
    print("🔧 Testing MCP Tool Execution...")
    
    # Test check_service_status tool
    try:
        print("Testing check_service_status...")
        result = await handle_lxd_tool("check-lxd", {
            "host": "localhost"
        })
        
        print(f"✅ Tool executed successfully!")
        if hasattr(result, 'text'):
            print(f"Result: {result.text[:200]}...")
        elif isinstance(result, list) and len(result) > 0 and hasattr(result[0], 'text'):
            print(f"Result: {result[0].text[:200]}...")
        else:
            print(f"Result: {str(result)[:200]}...")
            
    except Exception as e:
        print(f"❌ Tool execution failed: {e}")
    
    print()


async def test_lxd_installation():
    """Test the LXD installation tool that the user requested."""
    print("🐧 Testing LXD Installation Tool...")
    
    try:
        print("Testing install_lxd_on_system...")
        result = await handle_lxd_tool("install-lxd", {
            "host": "proxmoxpi.local"
        })
        
        print(f"✅ LXD installation tool executed!")
        if hasattr(result, 'text'):
            print(f"Result: {result.text}")
        elif isinstance(result, list) and len(result) > 0 and hasattr(result[0], 'text'):
            print(f"Result: {result[0].text}")
        else:
            print(f"Result: {str(result)}")
            
    except Exception as e:
        print(f"❌ LXD installation failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()


async def test_parse_tool_format():
    """Test parsing the **EXECUTE_TOOL:** format."""
    print("📝 Testing Tool Format Parsing...")
    
    # Import the chat interface to test tool parsing
    from start_homelab_chat import HomelabChatInterface, ChatConfig
    
    config = ChatConfig()
    chat = HomelabChatInterface(config)
    
    # Test parsing
    test_text = '**EXECUTE_TOOL:** install-lxd {"host": "proxmoxpi.local"}'
    
    result = await chat.parse_and_execute_tool(test_text)
    
    if result:
        print("✅ Tool parsing and execution successful!")
        print(f"Result: {result}")
    else:
        print("❌ Tool parsing failed or no tools found")
    
    print()


async def main():
    """Run all tests."""
    print("🧪 MCP Tool Integration Test Suite")
    print("=" * 50)
    
    await test_tool_discovery()
    await test_tool_execution()
    await test_lxd_installation()
    await test_parse_tool_format()
    
    print("✅ Test suite completed!")


if __name__ == "__main__":
    asyncio.run(main())