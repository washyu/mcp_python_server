#!/usr/bin/env python3
"""
Test client for the Ansible MCP Server

This script demonstrates how to connect to your MCP server and interact with it.
"""

import asyncio
import sys
from pathlib import Path

import anyio
import mcp.types as types
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def test_ansible_mcp_server():
    """Test the Ansible MCP server with various operations."""
    
    # Server parameters - using your main.py as entry point
    server_params = StdioServerParameters(
        command=sys.executable,  # Use current Python interpreter
        args=["main.py"],
        cwd=Path(__file__).parent,  # Run in current directory
    )
    
    print("Connecting to Ansible MCP Server...", file=sys.stderr)
    
    try:
        # Connect to the server
        async with stdio_client(server_params) as (read_stream, write_stream):
            # Create client session
            session = ClientSession(
                read_stream=read_stream,
                write_stream=write_stream,
            )
            
            # Start session in background
            async with anyio.create_task_group() as tg:
                tg.start_soon(session.start)
                
                # Initialize connection
                print("Initializing connection...", file=sys.stderr)
                init_result = await session.initialize()
                
                print(f"\n✓ Connected to: {init_result.serverInfo.name}", file=sys.stderr)
                print(f"  Version: {init_result.serverInfo.version}", file=sys.stderr)
                print(f"  Protocol: {init_result.protocolVersion}", file=sys.stderr)
                
                # List available tools
                print("\n=== Available Tools ===", file=sys.stderr)
                tools_result = await session.list_tools()
                
                if not tools_result.tools:
                    print("No tools available", file=sys.stderr)
                else:
                    for tool in tools_result.tools[:10]:  # Show first 10 tools
                        print(f"\n📦 {tool.name}", file=sys.stderr)
                        if tool.description:
                            print(f"   {tool.description}", file=sys.stderr)
                        if tool.inputSchema and 'properties' in tool.inputSchema:
                            props = tool.inputSchema.get('properties', {})
                            if props:
                                print(f"   Parameters:", file=sys.stderr)
                                for param, schema in props.items():
                                    required = param in tool.inputSchema.get('required', [])
                                    req_marker = "*" if required else ""
                                    desc = schema.get('description', 'No description')
                                    print(f"     - {param}{req_marker}: {desc}", file=sys.stderr)
                
                print(f"\n... and {len(tools_result.tools) - 10} more tools" if len(tools_result.tools) > 10 else "", file=sys.stderr)
                
                # Example tool calls
                print("\n=== Example Tool Calls ===", file=sys.stderr)
                
                # 1. List templates
                print("\n1. Listing templates...", file=sys.stderr)
                try:
                    templates_result = await session.call_tool(
                        name="list-templates",
                        arguments={}
                    )
                    print(f"   Found templates: {templates_result}", file=sys.stderr)
                except Exception as e:
                    print(f"   Error: {e}", file=sys.stderr)
                
                # 2. Get a specific SOP
                print("\n2. Getting VM creation SOP...", file=sys.stderr)
                try:
                    sop_result = await session.call_tool(
                        name="query-sop",
                        arguments={
                            "operation": "create_vm",
                            "detailed": True
                        }
                    )
                    if hasattr(sop_result, 'content'):
                        print(f"   SOP loaded successfully", file=sys.stderr)
                except Exception as e:
                    print(f"   Error: {e}", file=sys.stderr)
                
                # 3. Check inventory
                print("\n3. Checking Proxmox inventory...", file=sys.stderr)
                try:
                    inventory_result = await session.call_tool(
                        name="discover-proxmox-resources",
                        arguments={}
                    )
                    print(f"   Inventory discovered", file=sys.stderr)
                except Exception as e:
                    print(f"   Error: {e}", file=sys.stderr)
                
                # List resources if available
                print("\n=== Available Resources ===", file=sys.stderr)
                resources_result = await session.list_resources()
                
                if not resources_result.resources:
                    print("No resources available", file=sys.stderr)
                else:
                    for resource in resources_result.resources[:5]:
                        print(f"\n📄 {resource.name}", file=sys.stderr)
                        print(f"   URI: {resource.uri}", file=sys.stderr)
                        if resource.description:
                            print(f"   {resource.description}", file=sys.stderr)
                
                # List prompts if available
                print("\n=== Available Prompts ===", file=sys.stderr)
                prompts_result = await session.list_prompts()
                
                if not prompts_result.prompts:
                    print("No prompts available", file=sys.stderr)
                else:
                    for prompt in prompts_result.prompts:
                        print(f"\n💬 {prompt.name}", file=sys.stderr)
                        if prompt.description:
                            print(f"   {prompt.description}", file=sys.stderr)
                
                # Clean shutdown
                print("\n\nShutting down connection...", file=sys.stderr)
                await session.close()
                
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)


async def interactive_client():
    """Interactive client for testing specific tools."""
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["main.py"],
        cwd=Path(__file__).parent,
    )
    
    async with stdio_client(server_params) as (read_stream, write_stream):
        session = ClientSession(read_stream=read_stream, write_stream=write_stream)
        
        async with anyio.create_task_group() as tg:
            tg.start_soon(session.start)
            
            # Initialize
            await session.initialize()
            print("Connected! Enter 'help' for commands, 'quit' to exit.", file=sys.stderr)
            
            while True:
                try:
                    command = input("\n> ").strip()
                    
                    if command == "quit":
                        break
                    elif command == "help":
                        print("Commands:", file=sys.stderr)
                        print("  list tools - List all available tools", file=sys.stderr)
                        print("  call <tool> <args> - Call a tool with JSON args", file=sys.stderr)
                        print("  list resources - List all resources", file=sys.stderr)
                        print("  quit - Exit", file=sys.stderr)
                    elif command == "list tools":
                        result = await session.list_tools()
                        for tool in result.tools:
                            print(f"  - {tool.name}", file=sys.stderr)
                    elif command.startswith("call "):
                        parts = command.split(" ", 2)
                        if len(parts) >= 2:
                            tool_name = parts[1]
                            args = {}
                            if len(parts) == 3:
                                import json
                                args = json.loads(parts[2])
                            result = await session.call_tool(tool_name, args)
                            print(f"Result: {result}", file=sys.stderr)
                    elif command == "list resources":
                        result = await session.list_resources()
                        for resource in result.resources:
                            print(f"  - {resource.name}: {resource.uri}", file=sys.stderr)
                
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"Error: {e}", file=sys.stderr)
            
            await session.close()


if __name__ == "__main__":
    # Run the test
    print("Testing Ansible MCP Server...\n", file=sys.stderr)
    asyncio.run(test_ansible_mcp_server())
    
    # Uncomment to run interactive mode
    # asyncio.run(interactive_client())