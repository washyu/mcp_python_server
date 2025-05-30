#!/usr/bin/env python3
"""
Simple interactive AI agent for testing MCP tools.
Uses a stateless approach to avoid stdio conflicts.
"""

import asyncio
import json
import subprocess
from typing import Dict, Any, List
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from config import Config


console = Console()


def call_mcp_tool(tool_name: str, arguments: dict = None) -> str:
    """Call an MCP tool by running a one-shot command."""
    if arguments is None:
        arguments = {}
    
    # Create the requests as a single input
    requests = [
        {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "0.1.0",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0.1.0"}
            },
            "id": 1
        },
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": 2
        }
    ]
    
    # Send both requests
    input_data = "\n".join(json.dumps(r) for r in requests)
    
    # Run the server and get response
    result = subprocess.run(
        ["uv", "run", "python", "main.py"],
        input=input_data,
        capture_output=True,
        text=True
    )
    
    # Parse the last response (tool call result)
    lines = result.stdout.strip().split('\n')
    if len(lines) >= 2:
        try:
            response = json.loads(lines[-1])
            if "result" in response and "content" in response["result"]:
                for content in response["result"]["content"]:
                    if content.get("type") == "text":
                        return content["text"]
        except:
            pass
    
    return "Error calling tool"


class SimpleAIAgent:
    """Simple AI agent for testing."""
    
    def __init__(self):
        self.model = Config.OLLAMA_MODEL
        self.ollama_client = ollama.Client(**Config.get_ollama_client_params())
    
    def run(self):
        """Run the interactive agent."""
        console.print(Panel.fit(
            f"[bold cyan]Simple MCP Test Agent[/bold cyan]\n"
            f"Model: {self.model}\n"
            f"Ollama Host: {Config.OLLAMA_HOST}\n"
            f"Type 'quit' to exit",
            title="Welcome"
        ))
        
        # Check Ollama
        try:
            models = self.ollama_client.list()
            if not models['models']:
                console.print("[red]No models available in Ollama![/red]")
                return
        except Exception as e:
            console.print(f"[red]Cannot connect to Ollama: {e}[/red]")
            return
        
        console.print("\n[bold]Available MCP Tools:[/bold]")
        console.print("  • hello_world: Returns a greeting")
        
        # Conversation loop
        while True:
            user_input = Prompt.ask("\n[bold green]You[/bold green]")
            
            if user_input.lower() in ['quit', 'exit']:
                console.print("[yellow]Goodbye![/yellow]")
                break
            
            # Simple check for hello/greeting
            if any(word in user_input.lower() for word in ['hello', 'greet', 'tool']):
                console.print("\n[bold blue]AI[/bold blue]: I'll call the hello_world tool for you!")
                console.print("[dim]Calling tool: hello_world[/dim]")
                
                result = call_mcp_tool("hello_world")
                console.print(f"[green]Tool result: {result}[/green]")
            else:
                # Get AI response
                system_prompt = """You are a helpful assistant. You have access to a tool called 'hello_world' that returns a greeting.
                
If the user asks about greetings, hello, or wants to test tools, mention that you can call the hello_world tool."""
                
                response = self.ollama_client.chat(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_input}
                    ],
                    stream=False
                )
                
                console.print(f"\n[bold blue]AI[/bold blue]: {response['message']['content']}")


def main():
    """Main entry point."""
    agent = SimpleAIAgent()
    agent.run()


if __name__ == "__main__":
    main()