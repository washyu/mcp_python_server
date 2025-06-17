#!/usr/bin/env python3
"""
Universal Homelab MCP Server - Main Entry Point

🎯 Click Run/Debug in VS Code to start the AI chat interface!

This will automatically:
• Start the MCP WebSocket server
• Launch the AI chat interface
• Connect to your local Ollama AI
• Enable AI-driven homelab automation
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Ensure we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from src.server.mcp_server import main as mcp_main
from src.server.websocket_server import main as websocket_main


def main():
    """Entry point - supports both MCP server and chat interface."""
    parser = argparse.ArgumentParser(description="Universal Homelab MCP Server")
    parser.add_argument(
        "--mode",
        choices=["chat", "stdio", "websocket"],
        default="chat",
        help="Mode to run in: chat (full interface), stdio (MCP only), websocket (server only)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for WebSocket server (default: 8765)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "chat":
        # Full chat interface (default for VS Code debugging)
        print("🚀 Starting Homelab AI Chat Interface...", file=sys.stderr)
        from start_homelab_chat import main as start_chat
        asyncio.run(start_chat())
    elif args.mode == "stdio":
        # Use stdio transport (for Claude Desktop compatibility)
        asyncio.run(mcp_main())
    else:
        # Use WebSocket transport only
        print(f"Starting MCP WebSocket server on port {args.port}...", file=sys.stderr)
        asyncio.run(websocket_main())


if __name__ == "__main__":
    main()
