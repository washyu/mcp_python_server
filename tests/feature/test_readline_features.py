#!/usr/bin/env python3
"""
Test readline features in the chat interface
"""

import sys
import readline
from start_homelab_chat import HomelabChatInterface, ChatConfig

def test_readline_setup():
    """Test that readline is properly configured"""
    
    print("🧪 Testing Readline Configuration")
    print("="*50)
    
    # Create chat interface (this sets up readline)
    config = ChatConfig()
    chat = HomelabChatInterface(config)
    
    # Check if readline is available
    if hasattr(readline, 'get_history_length'):
        print("✅ Readline module is available")
        print(f"   History length: {readline.get_history_length()}")
    else:
        print("❌ Readline module not available")
        return
    
    # Check if history file exists
    from pathlib import Path
    history_file = Path.home() / ".homelab_chat_history"
    if history_file.exists():
        print(f"✅ History file exists: {history_file}")
        print(f"   File size: {history_file.stat().st_size} bytes")
    else:
        print(f"ℹ️  History file will be created: {history_file}")
    
    # Test tab completion
    print("\n🔧 Testing Tab Completion:")
    completer = chat._tab_completer
    
    test_completions = [
        ("he", "help"),
        ("sta", "status"), 
        ("My ho", "My homelab consists of"),
        ("I have", "I have a pi called"),
        ("dis", "discover")
    ]
    
    for text, expected in test_completions:
        result = completer(text, 0)
        if result and expected in result:
            print(f"   ✅ '{text}' → '{result}'")
        else:
            print(f"   ❌ '{text}' → '{result}' (expected: {expected})")
    
    print("\n📝 **Readline Features Available:**")
    print("   🔍 **History Navigation:**")
    print("      ↑ / ↓ arrows  - Browse command history")
    print("      Ctrl+R        - Reverse history search")
    print("   ")
    print("   ✏️  **Line Editing:**")
    print("      ← / → arrows  - Move cursor left/right")
    print("      Ctrl+A        - Go to beginning of line")
    print("      Ctrl+E        - Go to end of line")
    print("      Ctrl+K        - Delete from cursor to end")
    print("      Ctrl+U        - Delete entire line")
    print("      Ctrl+W        - Delete word before cursor")
    print("   ")
    print("   🎯 **Tab Completion:**")
    print("      Tab           - Complete commands and phrases")
    print("      Tab Tab       - Show all possible completions")
    print("\n🎉 **Ready to chat with full readline support!**")
    print("   Start with: python main.py --mode chat")

if __name__ == "__main__":
    test_readline_setup()