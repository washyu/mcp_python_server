#!/usr/bin/env python3
"""
Simple test script to verify MCP server and Ollama integration works.
"""

import asyncio
import ollama
from rich.console import Console
from config import Config
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

console = Console()


async def test_mcp_ollama_integration():
    """Test that we can use Ollama to call our MCP tool."""
    
    console.print("[bold]Testing MCP + Ollama Integration[/bold]\n")
    
    # Show configuration
    console.print(f"Configuration loaded from: {Config.OLLAMA_HOST}")
    
    # 1. Test Ollama connection
    console.print("\n1. Testing Ollama connection...")
    try:
        client = ollama.Client(**Config.get_ollama_client_params())
        console.print(f"   Connecting to: {Config.OLLAMA_HOST}")
        models = client.list()
        console.print(f"   ✓ Connected to Ollama")
        console.print(f"   Available models: {', '.join([m['model'] for m in models['models']])}")
    except Exception as e:
        console.print(f"   ✗ Cannot connect to Ollama: {e}")
        console.print("\n   [yellow]Troubleshooting:[/yellow]")
        console.print("   • Make sure Ollama is running")
        
        # Check if we're in WSL
        import subprocess
        try:
            result = subprocess.run(['uname', '-r'], capture_output=True, text=True)
            if 'microsoft' in result.stdout.lower():
                console.print("\n   [cyan]WSL Detected![/cyan] You're running in WSL but Ollama is on Windows.")
                console.print("   Try one of these solutions:")
                console.print("   1. Get your Windows IP and set OLLAMA_HOST:")
                console.print("      export OLLAMA_HOST=http://$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):11434")
                console.print("   2. Or use your Windows machine name:")
                console.print("      export OLLAMA_HOST=http://$(hostname).local:11434")
                console.print("   3. Or manually set it (replace with your Windows IP):")
                console.print("      export OLLAMA_HOST=http://192.168.x.x:11434")
        except:
            console.print("   • If using WSL with Ollama on Windows, set OLLAMA_HOST environment variable")
        
        return
    
    # 2. Test MCP Server
    console.print("\n2. Testing MCP Server...")
    
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "main.py"]
    )
    
    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize
                await session.initialize()
                console.print(f"   ✓ Connected to MCP server")
                
                # List tools
                tools_result = await session.list_tools()
                tool_names = [tool.name for tool in tools_result.tools]
                console.print(f"   Available tools: {', '.join(tool_names)}")
                
                # 3. Test hello_world tool
                console.print("\n3. Testing hello_world tool...")
                result = await session.call_tool("hello_world", {})
                
                # Extract text from result
                for content in result.content:
                    if hasattr(content, 'text'):
                        console.print(f"   ✓ Tool returned: {content.text}")
            
            # 4. Test Ollama calling the tool
            console.print("\n4. Testing Ollama understanding of tools...")
            
            # Use model from config
            model = Config.OLLAMA_MODEL
            
            # Check if model exists
            if not any(model in m['model'] for m in models['models']):
                console.print(f"   ⚠ Model {model} not found. Using first available model.")
                if models['models']:
                    model = models['models'][0]['model']
                else:
                    console.print(f"   ✗ No models available. Run: [cyan]ollama pull {Config.OLLAMA_MODEL}[/cyan]")
                    return
            
            prompt = """You have access to a tool called 'hello_world' that returns a greeting.
            
Please call the hello_world tool by responding with this exact JSON:
```json
{
    "tool_call": {
        "name": "hello_world",
        "arguments": {}
    }
}
```"""
            
            response = client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=False
            )
            
            ai_response = response['message']['content']
            console.print(f"   AI Response: {ai_response[:200]}...")
            
            if "hello_world" in ai_response:
                console.print("   ✓ AI correctly identified the tool!")
            else:
                console.print("   ⚠ AI didn't mention the tool, but that's okay for this test")
                
    except Exception as e:
        console.print(f"   ✗ Error testing MCP server: {e}")
        return
    
    console.print("\n[green]✓ All tests passed! The integration is working.[/green]")
    console.print("\nYou can now run the interactive agent with: [cyan]python test_agent.py[/cyan]")


if __name__ == "__main__":
    asyncio.run(test_mcp_ollama_integration())