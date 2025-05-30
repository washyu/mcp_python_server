#!/usr/bin/env python3
"""
Example MCP Client Implementation in Python

This demonstrates how to connect to an MCP server running as a subprocess
and interact with it using the built-in mcp.client classes.
"""

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import mcp.types as types
from mcp.client import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


class MCPClient:
    """A simple MCP client that connects to a server via stdio."""
    
    def __init__(self, server_script_path: str):
        """
        Initialize the MCP client.
        
        Args:
            server_script_path: Path to the MCP server Python script
        """
        self.server_params = StdioServerParameters(
            command="python",
            args=[server_script_path],
            env=None,  # Will use default environment
        )
        self.session = None
        self.read_stream = None
        self.write_stream = None
    
    @asynccontextmanager
    async def connect(self):
        """Connect to the MCP server and initialize the session."""
        # Create stdio transport connection
        async with stdio_client(self.server_params) as (read_stream, write_stream):
            # Create the client session
            self.session = ClientSession(
                read_stream=read_stream,
                write_stream=write_stream
            )
            
            # Start processing messages in the background
            async with anyio.create_task_group() as tg:
                tg.start_soon(self.session.start)
                
                # Initialize the connection
                try:
                    init_result = await self.session.initialize()
                    print(f"Connected to server: {init_result.serverInfo}")
                    
                    yield self
                    
                finally:
                    # Clean shutdown
                    await self.session.close()
    
    async def list_tools(self) -> list[types.Tool]:
        """List all available tools from the server."""
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        result = await self.session.list_tools()
        return result.tools
    
    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """
        Call a tool on the server.
        
        Args:
            name: Name of the tool to call
            arguments: Optional arguments to pass to the tool
            
        Returns:
            The tool's result
        """
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        result = await self.session.call_tool(name=name, arguments=arguments)
        return result
    
    async def list_resources(self) -> list[types.Resource]:
        """List all available resources from the server."""
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        result = await self.session.list_resources()
        return result.resources
    
    async def read_resource(self, uri: str) -> Any:
        """Read a specific resource."""
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        result = await self.session.read_resource(uri=uri)
        return result
    
    async def list_prompts(self) -> list[types.Prompt]:
        """List all available prompts from the server."""
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        result = await self.session.list_prompts()
        return result.prompts
    
    async def get_prompt(self, name: str, arguments: dict[str, str] | None = None) -> Any:
        """Get a specific prompt."""
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        result = await self.session.get_prompt(name=name, arguments=arguments)
        return result


async def main():
    """Example usage of the MCP client."""
    
    # Path to your MCP server script
    server_path = "server.py"  # Update this to your server script path
    
    # Create client instance
    client = MCPClient(server_path)
    
    try:
        # Connect to the server
        async with client.connect():
            print("Successfully connected to MCP server!")
            
            # List available tools
            print("\n=== Available Tools ===")
            tools = await client.list_tools()
            for tool in tools:
                print(f"- {tool.name}: {tool.description}")
                if tool.inputSchema:
                    print(f"  Input schema: {tool.inputSchema}")
            
            # Example: Call a tool (replace with actual tool name and args)
            # result = await client.call_tool(
            #     name="example_tool",
            #     arguments={"param1": "value1"}
            # )
            # print(f"Tool result: {result}")
            
            # List available resources
            print("\n=== Available Resources ===")
            resources = await client.list_resources()
            for resource in resources:
                print(f"- {resource.uri}: {resource.name}")
                if resource.description:
                    print(f"  {resource.description}")
            
            # List available prompts
            print("\n=== Available Prompts ===")
            prompts = await client.list_prompts()
            for prompt in prompts:
                print(f"- {prompt.name}: {prompt.description}")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise


# Alternative: Direct usage without the wrapper class
async def direct_client_example():
    """Example of using the MCP client directly without a wrapper class."""
    
    # Define server parameters
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
    )
    
    # Connect and interact with the server
    async with stdio_client(server_params) as (read_stream, write_stream):
        # Create session
        session = ClientSession(read_stream, write_stream)
        
        # Start the session message processing
        async with anyio.create_task_group() as tg:
            tg.start_soon(session.start)
            
            # Initialize connection
            init_result = await session.initialize()
            print(f"Server info: {init_result.serverInfo}")
            
            # List and call tools
            tools_result = await session.list_tools()
            for tool in tools_result.tools:
                print(f"Tool: {tool.name}")
            
            # Call a specific tool
            # tool_result = await session.call_tool(
            #     name="tool_name",
            #     arguments={"key": "value"}
            # )
            
            await session.close()


if __name__ == "__main__":
    # Import anyio here to avoid import errors if not needed
    import anyio
    
    # Run the example
    asyncio.run(main())
    
    # Or run the direct example
    # asyncio.run(direct_client_example())