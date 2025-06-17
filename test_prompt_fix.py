#!/usr/bin/env python3
"""
Test the enhanced prompt formatting fix.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from start_homelab_chat import HomelabChatInterface, ChatConfig


async def test_prompt_generation():
    """Test the enhanced prompt generation without f-string issues."""
    print("🧪 Testing Enhanced Prompt Generation...")
    
    config = ChatConfig()
    chat = HomelabChatInterface(config)
    
    try:
        message = "could you install lxd on to my pi the server hostname is proxmoxpi.local"
        prompt = await chat.create_enhanced_prompt(message)
        
        print("✅ Prompt generated successfully!")
        print(f"Prompt length: {len(prompt)} characters")
        
        # Check if the tool examples are properly formatted
        if "**EXECUTE_TOOL:** install-lxd" in prompt:
            print("✅ Tool examples are properly formatted")
        else:
            print("❌ Tool examples not found in prompt")
            
        # Check if JSON braces are properly escaped
        if '{"host":' in prompt:
            print("✅ JSON braces are properly escaped")
        else:
            print("❌ JSON braces not found")
            
        return True
        
    except Exception as e:
        print(f"❌ Prompt generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the test."""
    print("🔧 Testing Enhanced Prompt Fix")
    print("=" * 40)
    
    success = await test_prompt_generation()
    
    if success:
        print("\n✅ All tests passed! The chat interface should work now.")
    else:
        print("\n❌ Tests failed - need to investigate further.")


if __name__ == "__main__":
    asyncio.run(main())