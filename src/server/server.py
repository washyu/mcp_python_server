import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio
from src.utils.config import Config

# Create the MCP server instance
app = Server(Config.MCP_SERVER_NAME)

# Define the hello_world tool
@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="hello_world",
            description="A simple tool that returns 'Hello, World!'",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    if name == "hello_world":
        return [TextContent(type="text", text="Hello, World!")]
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    """Run the MCP server."""
    # Run the server using stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())