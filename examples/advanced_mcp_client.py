#!/usr/bin/env python3
"""
Advanced MCP Client Implementation with Progress Tracking and Custom Handlers

This demonstrates more advanced features of the MCP client including:
- Progress callbacks for long-running operations
- Custom message handlers
- Logging callbacks
- Error handling
"""

import asyncio
import json
import sys
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any, Optional

import anyio
import mcp.types as types
from mcp.client import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.shared.context import RequestContext


class AdvancedMCPClient:
    """An advanced MCP client with progress tracking and custom handlers."""
    
    def __init__(self, server_script_path: str, log_messages: bool = True):
        """
        Initialize the advanced MCP client.
        
        Args:
            server_script_path: Path to the MCP server Python script
            log_messages: Whether to log server messages
        """
        self.server_params = StdioServerParameters(
            command="python",
            args=[server_script_path],
            env=None,
        )
        self.session = None
        self.log_messages = log_messages
        self.pending_operations = {}
    
    async def _handle_logging(self, params: types.LoggingMessageNotificationParams):
        """Handle logging messages from the server."""
        if self.log_messages:
            level = params.level
            message = params.data if isinstance(params.data, str) else json.dumps(params.data)
            print(f"[SERVER {level}] {message}")
    
    async def _handle_message(
        self,
        message: types.ServerRequest | types.ServerNotification | Exception
    ):
        """Handle incoming messages from the server."""
        if isinstance(message, Exception):
            print(f"[ERROR] Received exception: {message}")
        elif hasattr(message, 'method'):
            print(f"[MESSAGE] Received: {getattr(message, 'method', 'unknown')}")
    
    async def _handle_progress(
        self,
        progress_token: str | int,
        progress: float,
        total: Optional[float] = None,
        message: Optional[str] = None
    ):
        """Handle progress updates for long-running operations."""
        if total:
            percent = (progress / total) * 100
            print(f"[PROGRESS] {progress_token}: {percent:.1f}% - {message or ''}")
        else:
            print(f"[PROGRESS] {progress_token}: {progress} - {message or ''}")
    
    @asynccontextmanager
    async def connect(self):
        """Connect to the MCP server with custom handlers."""
        async with stdio_client(self.server_params) as (read_stream, write_stream):
            # Create session with custom callbacks
            self.session = ClientSession(
                read_stream=read_stream,
                write_stream=write_stream,
                logging_callback=self._handle_logging,
                message_handler=self._handle_message,
                read_timeout_seconds=timedelta(seconds=30),
            )
            
            async with anyio.create_task_group() as tg:
                tg.start_soon(self.session.start)
                
                try:
                    # Initialize with extended timeout for slow servers
                    init_result = await self.session.initialize()
                    print(f"Connected to: {init_result.serverInfo.name} v{init_result.serverInfo.version}")
                    
                    # Log server capabilities
                    if init_result.capabilities:
                        print("\nServer Capabilities:")
                        if init_result.capabilities.tools:
                            print("  ✓ Tools")
                        if init_result.capabilities.resources:
                            print("  ✓ Resources")
                        if init_result.capabilities.prompts:
                            print("  ✓ Prompts")
                        if init_result.capabilities.logging:
                            print("  ✓ Logging")
                    
                    yield self
                    
                finally:
                    await self.session.close()
    
    async def call_tool_with_progress(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        timeout_seconds: int = 300
    ) -> Any:
        """
        Call a tool with progress tracking.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            timeout_seconds: Operation timeout in seconds
            
        Returns:
            Tool result
        """
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        # Create a progress callback
        progress_token = f"{name}_{id(arguments)}"
        
        async def progress_callback(token: str | int, progress: float, total: Optional[float] = None, message: Optional[str] = None):
            await self._handle_progress(token, progress, total, message)
        
        # Call tool with progress tracking
        result = await self.session.call_tool(
            name=name,
            arguments=arguments,
            read_timeout_seconds=timedelta(seconds=timeout_seconds),
            progress_callback=progress_callback
        )
        
        return result
    
    async def set_server_logging_level(self, level: types.LoggingLevel):
        """
        Set the server's logging level.
        
        Args:
            level: The logging level (debug, info, warning, error)
        """
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        result = await self.session.set_logging_level(level)
        print(f"Logging level set to: {level}")
        return result
    
    async def batch_tool_calls(self, tool_calls: list[dict[str, Any]]) -> list[Any]:
        """
        Execute multiple tool calls concurrently.
        
        Args:
            tool_calls: List of dicts with 'name' and 'arguments' keys
            
        Returns:
            List of results in the same order as inputs
        """
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        async def call_single_tool(tool_spec: dict[str, Any]) -> Any:
            return await self.call_tool_with_progress(
                name=tool_spec['name'],
                arguments=tool_spec.get('arguments')
            )
        
        # Execute all calls concurrently
        results = await asyncio.gather(
            *[call_single_tool(spec) for spec in tool_calls],
            return_exceptions=True
        )
        
        # Check for errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Error in tool call {tool_calls[i]['name']}: {result}")
        
        return results
    
    async def subscribe_to_resource(self, uri: str) -> None:
        """Subscribe to resource updates."""
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        result = await self.session.subscribe_resource(uri=uri)
        print(f"Subscribed to resource: {uri}")
        return result
    
    async def unsubscribe_from_resource(self, uri: str) -> None:
        """Unsubscribe from resource updates."""
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        result = await self.session.unsubscribe_resource(uri=uri)
        print(f"Unsubscribed from resource: {uri}")
        return result


async def example_with_progress():
    """Example showing progress tracking and advanced features."""
    
    client = AdvancedMCPClient("server.py", log_messages=True)
    
    async with client.connect():
        # Set logging level to debug
        await client.set_server_logging_level(types.LoggingLevel.debug)
        
        # Example: Call a long-running tool with progress
        print("\n=== Calling tool with progress tracking ===")
        # result = await client.call_tool_with_progress(
        #     name="long_running_tool",
        #     arguments={"iterations": 100},
        #     timeout_seconds=600
        # )
        
        # Example: Batch multiple tool calls
        print("\n=== Batch tool calls ===")
        # batch_results = await client.batch_tool_calls([
        #     {"name": "tool1", "arguments": {"param": "value1"}},
        #     {"name": "tool2", "arguments": {"param": "value2"}},
        #     {"name": "tool3", "arguments": {"param": "value3"}},
        # ])
        
        # Example: Subscribe to resource updates
        print("\n=== Resource subscription ===")
        # await client.subscribe_to_resource("file:///path/to/watched/file")
        # ... do some work ...
        # await client.unsubscribe_from_resource("file:///path/to/watched/file")


# Example: Client with custom handlers
class CustomHandlerClient(AdvancedMCPClient):
    """Example of extending the client with custom behavior."""
    
    def __init__(self, server_script_path: str):
        super().__init__(server_script_path)
        self.tool_call_count = 0
        self.resource_access_count = 0
    
    async def call_tool_with_progress(self, name: str, arguments: dict[str, Any] | None = None, timeout_seconds: int = 300) -> Any:
        """Override to add custom tracking."""
        self.tool_call_count += 1
        print(f"[METRICS] Tool call #{self.tool_call_count}: {name}")
        
        result = await super().call_tool_with_progress(name, arguments, timeout_seconds)
        
        # Process result
        if hasattr(result, 'content'):
            print(f"[RESULT] Tool returned {len(str(result.content))} chars")
        
        return result
    
    async def read_resource(self, uri: str) -> Any:
        """Override to add custom tracking."""
        self.resource_access_count += 1
        print(f"[METRICS] Resource access #{self.resource_access_count}: {uri}")
        
        return await super().read_resource(uri)


if __name__ == "__main__":
    # Run the advanced example
    asyncio.run(example_with_progress())