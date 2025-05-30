#!/usr/bin/env python3
"""
Simple AI agent that uses Ollama for LLM and our MCP server for tools.
This allows fully local testing of the MCP server.
"""

import asyncio
import json
from typing import Dict, Any, List
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from config import Config
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

console = Console()


class LocalAIAgent:
    """A simple AI agent that uses Ollama and MCP tools."""
    
    def __init__(self, model: str = None):
        # Use model from config or override
        self.model = model or Config.OLLAMA_MODEL
        # Initialize Ollama client with config
        self.ollama_client = ollama.Client(**Config.get_ollama_client_params())
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
        
        # Check if Ollama is running and model is available
        try:
            models = self.ollama_client.list()
            model_names = [m['model'] for m in models['models']]
            if not any(self.model in name for name in model_names):
                console.print(f"[yellow]Warning: Model {self.model} not found in Ollama.[/yellow]")
                console.print(f"Available models: {', '.join(model_names)}")
                console.print(f"\nTo download the model, run: [cyan]ollama pull {self.model}[/cyan]")
                return
        except Exception as e:
            console.print(f"[red]Error: Cannot connect to Ollama. Make sure it's running.[/red]")
            console.print(f"Start Ollama with: [cyan]ollama serve[/cyan]")
            return
        
        # Set up MCP server connection
        server_params = StdioServerParameters(
            command="uv",
            args=["run", "python", "main.py"]
        )
        
        # Connect to MCP server
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize the session
                await session.initialize()
                
                # Display available tools
                tools_result = await session.list_tools()
                console.print("\n[bold]Available MCP Tools:[/bold]")
                for tool in tools_result.tools:
                    console.print(f"  • {tool.name}: {tool.description}")
                
                # Main conversation loop
                while True:
                    # Get user input
                    user_input = Prompt.ask("\n[bold green]You[/bold green]")
                    
                    if user_input.lower() in ['quit', 'exit', 'bye']:
                        console.print("[yellow]Goodbye![/yellow]")
                        break
                    
                    # Add user message to history
                    self.conversation_history.append({
                        "role": "user",
                        "content": user_input
                    })
                    
                    # Create system prompt with tool information
                    system_prompt = self._create_system_prompt(tools_result.tools)
                    
                    # Get AI response
                    console.print("\n[bold blue]AI[/bold blue]: ", end="")
                    response = await self._get_ai_response(system_prompt, user_input)
                    
                    # Check if AI wants to use a tool
                    tool_calls = self._extract_tool_calls(response)
                    
                    if tool_calls:
                        # Execute tool calls
                        for tool_call in tool_calls:
                            tool_name = tool_call.get("name")
                            tool_args = tool_call.get("arguments", {})
                            
                            console.print(f"\n[dim]Calling tool: {tool_name}[/dim]")
                            
                            try:
                                result = await session.call_tool(tool_name, tool_args)
                                
                                # Extract text from result
                                result_text = ""
                                for content in result.content:
                                    if hasattr(content, 'text'):
                                        result_text = content.text
                                        break
                                
                                console.print(f"[green]Tool result: {result_text}[/green]")
                                
                                # Add tool result to conversation
                                self.conversation_history.append({
                                    "role": "assistant",
                                    "content": f"Tool '{tool_name}' returned: {result_text}"
                                })
                            except Exception as e:
                                console.print(f"[red]Error calling tool: {e}[/red]")
                    else:
                        # Just display the AI response
                        console.print(response)
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": response
                        })
    
    def _create_system_prompt(self, tools: List[Any]) -> str:
        """Create a system prompt that includes tool information."""
        tool_descriptions = []
        for tool in tools:
            tool_descriptions.append(
                f"- {tool.name}: {tool.description}"
            )
        
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
    
    async def _get_ai_response(self, system_prompt: str, user_input: str) -> str:
        """Get response from Ollama."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        response = self.ollama_client.chat(
            model=self.model,
            messages=messages,
            stream=False
        )
        
        return response['message']['content']
    
    def _extract_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """Extract tool calls from AI response."""
        tool_calls = []
        
        # Look for JSON blocks in the response
        if "```json" in response:
            try:
                # Extract JSON between ```json and ```
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
                
                data = json.loads(json_str)
                if "tool_call" in data:
                    tool_calls.append(data["tool_call"])
            except json.JSONDecodeError:
                pass
        
        return tool_calls


async def main():
    """Main entry point."""
    agent = LocalAIAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())