#!/usr/bin/env python3
"""
Interactive AI agent that uses Ollama and MCP tools.
This version properly handles stdio without conflicts.
"""

import asyncio
import json
import sys
from typing import Dict, Any, List
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from config import Config
import subprocess


console = Console()


class MCPToolClient:
    """Simple client to interact with MCP server via subprocess."""
    
    def __init__(self):
        self.process = None
        self.tools = []
    
    async def connect(self):
        """Start MCP server and get available tools."""
        # Start the server process
        self.process = await asyncio.create_subprocess_exec(
            "uv", "run", "python", "main.py",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        
        # Initialize connection
        await self._send_and_receive({
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "0.1.0",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-agent",
                    "version": "0.1.0"
                }
            },
            "id": 1
        })
        
        # Get tools
        response = await self._send_and_receive({
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        })
        
        if "result" in response and "tools" in response["result"]:
            self.tools = response["result"]["tools"]
    
    async def _send_and_receive(self, request: dict) -> dict:
        """Send request and get response."""
        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str.encode())
        await self.process.stdin.drain()
        
        response_line = await self.process.stdout.readline()
        return json.loads(response_line.decode())
    
    async def call_tool(self, name: str, arguments: dict = None) -> str:
        """Call a tool and return the result."""
        response = await self._send_and_receive({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments or {}
            },
            "id": 3
        })
        
        # Extract text from response
        if "result" in response and "content" in response["result"]:
            for content in response["result"]["content"]:
                if content.get("type") == "text":
                    return content["text"]
        
        return str(response)
    
    async def disconnect(self):
        """Disconnect from server."""
        if self.process:
            self.process.terminate()
            await self.process.wait()


class LocalAIAgent:
    """AI agent that uses Ollama and MCP tools."""
    
    def __init__(self):
        self.model = Config.OLLAMA_MODEL
        self.ollama_client = ollama.Client(**Config.get_ollama_client_params())
        self.mcp_client = MCPToolClient()
        self.conversation_history = []
    
    async def run(self):
        """Run the interactive agent."""
        console.print(Panel.fit(
            f"[bold cyan]Local AI Agent[/bold cyan]\n"
            f"Model: {self.model}\n"
            f"Ollama Host: {Config.OLLAMA_HOST}\n"
            f"Type 'quit' to exit",
            title="Welcome"
        ))
        
        # Check Ollama connection
        try:
            models = self.ollama_client.list()
            model_names = [m['model'] for m in models['models']]
            if not any(self.model in name for name in model_names):
                console.print(f"[yellow]Warning: Model {self.model} not found.[/yellow]")
                console.print(f"Available models: {', '.join(model_names)}")
                return
        except Exception as e:
            console.print(f"[red]Error: Cannot connect to Ollama: {e}[/red]")
            return
        
        # Connect to MCP server
        try:
            console.print("\nConnecting to MCP server...")
            await self.mcp_client.connect()
            
            console.print("\n[bold]Available MCP Tools:[/bold]")
            for tool in self.mcp_client.tools:
                console.print(f"  • {tool['name']}: {tool['description']}")
        except Exception as e:
            console.print(f"[red]Error connecting to MCP server: {e}[/red]")
            return
        
        # Main conversation loop
        try:
            while True:
                # Get user input
                user_input = Prompt.ask("\n[bold green]You[/bold green]")
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    console.print("[yellow]Goodbye![/yellow]")
                    break
                
                # Create system prompt
                system_prompt = self._create_system_prompt()
                
                # Get AI response
                console.print("\n[bold blue]AI[/bold blue]: ", end="")
                response = self._get_ai_response(system_prompt, user_input)
                
                # Check for tool calls
                tool_calls = self._extract_tool_calls(response)
                
                if tool_calls:
                    for tool_call in tool_calls:
                        tool_name = tool_call.get("name")
                        tool_args = tool_call.get("arguments", {})
                        
                        console.print(f"\n[dim]Calling tool: {tool_name}[/dim]")
                        
                        try:
                            result = await self.mcp_client.call_tool(tool_name, tool_args)
                            console.print(f"[green]Tool result: {result}[/green]")
                        except Exception as e:
                            console.print(f"[red]Error: {e}[/red]")
                else:
                    console.print(response)
                    
        finally:
            await self.mcp_client.disconnect()
    
    def _create_system_prompt(self) -> str:
        """Create system prompt with tool info."""
        tool_descriptions = []
        for tool in self.mcp_client.tools:
            tool_descriptions.append(f"- {tool['name']}: {tool['description']}")
        
        return f"""You are a helpful AI assistant with access to the following tools:

{chr(10).join(tool_descriptions)}

When you want to use a tool, respond with a JSON block like this:
```json
{{
    "tool_call": {{
        "name": "tool_name",
        "arguments": {{}}
    }}
}}
```

Otherwise, respond normally with helpful text."""
    
    def _get_ai_response(self, system_prompt: str, user_input: str) -> str:
        """Get response from Ollama."""
        response = self.ollama_client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            stream=False
        )
        return response['message']['content']
    
    def _extract_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """Extract tool calls from response."""
        tool_calls = []
        
        if "```json" in response:
            try:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
                
                data = json.loads(json_str)
                if "tool_call" in data:
                    tool_calls.append(data["tool_call"])
            except:
                pass
        
        return tool_calls


async def main():
    """Main entry point."""
    agent = LocalAIAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())