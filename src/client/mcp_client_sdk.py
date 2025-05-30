"""
MCP client using the official SDK.
"""

import asyncio
from typing import Any, Dict, List, Optional
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.types import Tool
import anyio


class MCPClientSDK:
    """MCP client using the official SDK."""
    
    def __init__(self, server_command: List[str] = None):
        if server_command is None:
            server_command = ["uv", "run", "python", "main.py"]
        
        self.server_params = StdioServerParameters(
            command=server_command[0],
            args=server_command[1:] if len(server_command) > 1 else [],
            env=None
        )
        self.session: Optional[ClientSession] = None
        self.tools: Dict[str, Tool] = {}
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # The session cleanup is handled by the context managers
        pass
    
    async def connect(self):
        """Connect to the MCP server and initialize session."""
        # This will be set up when we enter the context
        pass
    
    async def run_session(self):
        """Run the MCP session."""
        async with stdio_client(self.server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                self.session = session
                
                # Initialize the connection
                await session.initialize()
                
                # Get available tools
                tools_result = await session.list_tools()
                self.tools = {tool.name: tool for tool in tools_result.tools}
                
                # Keep session alive
                await anyio.sleep_forever()
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> str:
        """Call a tool and return the result."""
        if arguments is None:
            arguments = {}
        
        if not self.session:
            raise Exception("Not connected to MCP server")
        
        result = await self.session.call_tool(tool_name, arguments)
        
        # Extract text content from result
        if result.content and len(result.content) > 0:
            for content in result.content:
                if hasattr(content, 'text'):
                    return content.text
        
        return f"Tool returned: {result}"
    
    def list_tools(self) -> List[Tool]:
        """Get list of available tools."""
        return list(self.tools.values())


async def test_mcp_client():
    """Test the MCP client."""
    print("Testing MCP Client with SDK...")
    
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "main.py"]
    )
    
    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize
                print("Initializing session...")
                init_result = await session.initialize()
                print(f"Server: {init_result.serverInfo}")
                
                # List tools  
                print("\nListing tools...")
                tools_result = await session.list_tools()
                for tool in tools_result.tools:
                    print(f"  - {tool.name}: {tool.description}")
                
                # Call hello_world tool
                print("\nCalling hello_world tool...")
                result = await session.call_tool("hello_world", {})
                
                # Extract text from result
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(f"Result: {content.text}")
                
                print("\nTest completed successfully!")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_mcp_client())