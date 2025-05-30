#!/usr/bin/env python3
"""
Test WebSocket MCP server and client together.
"""

import asyncio
import sys
from websocket_server import MCPWebSocketServer
from websocket_client import test_websocket_client


async def run_test():
    """Run server and client test together."""
    # Start server in background
    server = MCPWebSocketServer(port=8765)
    server_task = asyncio.create_task(server.start())
    
    # Give server time to start
    await asyncio.sleep(1)
    
    try:
        # Run client test
        await test_websocket_client()
    finally:
        # Cancel server
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    # Run with minimal logging
    import logging
    logging.getLogger("websockets").setLevel(logging.WARNING)
    
    asyncio.run(run_test())