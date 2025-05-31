import asyncio
import sys
import argparse
from src.server.mcp_server import main as mcp_main
from src.server.websocket_server import main as websocket_main


def main():
    """Entry point for the MCP server."""
    parser = argparse.ArgumentParser(description="Ansible MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "websocket"],
        default="websocket",
        help="Transport method to use (default: websocket)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for WebSocket server (default: 8765)"
    )
    
    args = parser.parse_args()
    
    if args.transport == "stdio":
        # Use stdio transport (for Claude Desktop compatibility)
        asyncio.run(mcp_main())
    else:
        # Use WebSocket transport (default)
        print(f"Starting MCP WebSocket server on port {args.port}...", file=sys.stderr)
        asyncio.run(websocket_main())


if __name__ == "__main__":
    main()
