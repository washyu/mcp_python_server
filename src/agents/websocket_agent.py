#!/usr/bin/env python3
"""
Interactive AI agent using WebSocket MCP connection with wizard support.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

import ollama
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from config import Config
from src.client.websocket_client import MCPWebSocketClient
from src.utils.setup_wizard import WizardFlow, PROXMOX_WIZARD_FLOW
from src.utils.profile_manager import ProfileManager
from src.utils.proxmox_tools import ProxmoxConnectionTest

console = Console()


class WebSocketAIAgent:
    """AI agent with wizard support that uses Ollama and WebSocket MCP server."""
    
    def __init__(self):
        self.model = Config.OLLAMA_MODEL
        self.ollama_client = ollama.Client(**Config.get_ollama_client_params())
        self.mcp_uri = "ws://localhost:8765"
        self.wizard_flow = WizardFlow()
        self.active_wizard = None
        self.wizard_context = {}
        self.profile_manager = ProfileManager()
        
        # Define available wizards
        self.wizard_flow.define_flow("proxmox_setup", PROXMOX_WIZARD_FLOW)
        
        # VM creation wizard
        self.wizard_flow.define_flow("quick_vm_setup", [
            {
                "key": "vm_name",
                "prompt": "What would you like to name your new VM?",
                "validator": lambda x: (True, "") if x and x.replace("-", "").replace("_", "").isalnum() else (False, "VM name must be alphanumeric with hyphens/underscores only")
            },
            {
                "key": "vm_type",
                "prompt": "What type of VM do you need? (web-server, database, dev-environment, custom)",
                "options": ["web-server", "database", "dev-environment", "custom"],
                "default": "web-server"
            },
            {
                "key": "vm_size",
                "prompt": "What size VM do you need? (small: 2CPU/4GB, medium: 4CPU/8GB, large: 8CPU/16GB)",
                "options": ["small", "medium", "large"],
                "default": "medium"
            }
        ])
    
    async def run(self):
        """Run the interactive agent."""
        console.print(Panel.fit(
            f"[bold cyan]WebSocket AI Agent with Wizard Support[/bold cyan]\n"
            f"Model: {self.model}\n"
            f"Ollama Host: {Config.OLLAMA_HOST}\n"
            f"MCP Server: {self.mcp_uri}\n\n"
            f"[yellow]Special Commands:[/yellow]\n"
            f"  • 'setup proxmox' - Configure Proxmox connection\n"
            f"  • 'show config' - Show current Proxmox configuration\n"
            f"  • 'test connection' - Test Proxmox connection\n"
            f"  • 'create vm' - Quick VM creation wizard\n"
            f"  • 'quit' - Exit the agent",
            title="Welcome"
        ))
        
        # Check Ollama
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
            async with MCPWebSocketClient(self.mcp_uri) as mcp_client:
                console.print(f"\n✓ Connected to MCP server at {self.mcp_uri}")
                
                # Display available tools
                console.print("\n[bold]Available MCP Tools:[/bold]")
                for tool in mcp_client.tools.values():
                    console.print(f"  • {tool.name}: {tool.description}")
                
                # Main conversation loop
                while True:
                    # Check if we're in a wizard flow
                    if self.active_wizard:
                        prompt_text = self._format_wizard_prompt()
                    else:
                        prompt_text = "\n[bold green]You[/bold green]"
                    
                    # Get user input
                    user_input = Prompt.ask(prompt_text)
                    
                    if user_input.lower() in ['quit', 'exit', 'bye']:
                        console.print("[yellow]Goodbye![/yellow]")
                        break
                    
                    # Handle wizard flow
                    if self.active_wizard:
                        await self._handle_wizard_response(user_input, mcp_client)
                        continue
                    
                    # Check for wizard triggers
                    wizard_started = await self._check_wizard_trigger(user_input)
                    if wizard_started:
                        continue
                    
                    # Normal AI interaction
                    await self._handle_ai_interaction(user_input, mcp_client)
                        
        except Exception as e:
            console.print(f"[red]Error connecting to MCP server: {e}[/red]")
            console.print("\nMake sure the WebSocket MCP server is running:")
            console.print("  [cyan]uv run python main.py --transport websocket[/cyan]")
    
    def _create_system_prompt(self, tools: List[Any]) -> str:
        """Create a system prompt that includes tool information."""
        tool_descriptions = []
        for tool in tools:
            tool_descriptions.append(f"- {tool.name}: {tool.description}")
        
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
        """Extract tool calls from AI response."""
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
    
    def _format_wizard_prompt(self) -> str:
        """Format the prompt for wizard mode."""
        if not self.wizard_context:
            return "\n[bold green]You[/bold green]"
        
        step = self.wizard_context
        prompt = f"\n[bold cyan]Wizard[/bold cyan]: {step['prompt']}"
        
        if step.get('options'):
            prompt += f" ({'/'.join(step['options'])})"
        
        if step.get('default'):
            prompt += f"\n[dim]Default: {step['default']}[/dim]"
        
        return prompt
    
    async def _handle_wizard_response(self, response: str, mcp_client) -> None:
        """Handle response during wizard flow."""
        # Use default if empty response
        if not response and self.wizard_context.get('default'):
            response = self.wizard_context['default']
        
        # Process the response
        _, result = self.wizard_flow.process_response(self.active_wizard, response)
        
        if result['type'] == 'error':
            console.print(f"[red]Error: {result['message']}[/red]")
            self.wizard_context = {
                'prompt': result['retry_prompt'],
                'key': self.wizard_context['key'],
                'options': self.wizard_context.get('options'),
                'default': self.wizard_context.get('default')
            }
        elif result['type'] == 'complete':
            console.print("\n[green]Wizard completed![/green]")
            console.print("\n[bold]Collected Data:[/bold]")
            
            # Display collected data (mask passwords)
            for key, value in result['data'].items():
                display_value = value
                if 'password' in key.lower():
                    display_value = '*' * min(len(str(value)), 8)
                console.print(f"  • {key}: {display_value}")
            
            # Process the wizard results
            await self._process_wizard_results(self.active_wizard, result['data'], mcp_client)
            
            # Reset wizard state
            self.active_wizard = None
            self.wizard_context = {}
        else:
            # Next step
            self.wizard_context = result
    
    async def _check_wizard_trigger(self, user_input: str) -> bool:
        """Check if user input triggers a wizard flow."""
        input_lower = user_input.lower()
        
        if "setup proxmox" in input_lower or "configure proxmox" in input_lower:
            console.print("\n[bold cyan]Starting Proxmox Setup Wizard[/bold cyan]")
            self.active_wizard = "proxmox_setup"
            self.wizard_context = self.wizard_flow.start_flow("proxmox_setup")
            return True
        
        elif "create vm" in input_lower or "new vm" in input_lower:
            console.print("\n[bold cyan]Starting VM Creation Wizard[/bold cyan]")
            self.active_wizard = "quick_vm_setup"
            self.wizard_context = self.wizard_flow.start_flow("quick_vm_setup")
            return True
        
        elif "show config" in input_lower or "show proxmox" in input_lower:
            await self._show_config()
            return True
        
        elif "test connection" in input_lower or "test proxmox" in input_lower:
            await self._test_connection()
            return True
        
        return False
    
    async def _process_wizard_results(self, wizard_name: str, data: Dict[str, Any], mcp_client=None) -> None:
        """Process completed wizard results."""
        if wizard_name == "proxmox_setup":
            # Test the connection first
            connection_ok = await ProxmoxConnectionTest.test_and_display(
                data["proxmox_host"],
                data["proxmox_user"],
                data["proxmox_password"],
                data["verify_ssl"]
            )
            
            if not connection_ok:
                console.print("\n[yellow]Would you like to:[/yellow]")
                console.print("  1. Try again with different credentials")
                console.print("  2. Save anyway (fix later)")
                console.print("  3. Cancel")
                
                choice = Prompt.ask("Choose option", choices=["1", "2", "3"], default="1")
                
                if choice == "1":
                    # Restart the wizard
                    self.active_wizard = "proxmox_setup"
                    self.wizard_context = self.wizard_flow.start_flow("proxmox_setup")
                    return
                elif choice == "3":
                    console.print("[yellow]Setup cancelled.[/yellow]")
                    return
                # If choice == "2", continue to save
            
            # For single server setup, always save to a default profile
            profile_name = "main"
            
            # Convert wizard data to config format
            config = {
                "PROXMOX_HOST": data["proxmox_host"],
                "PROXMOX_USER": data["proxmox_user"],
                "PROXMOX_PASSWORD": data["proxmox_password"],
                "PROXMOX_VERIFY_SSL": data["verify_ssl"]
            }
            
            # Save and activate the profile
            await self.profile_manager.create_profile(profile_name, config)
            await self.profile_manager.set_active_profile(profile_name)
            await self.profile_manager.export_to_env(profile_name)
            
            console.print(f"\n[green]✓ Proxmox configuration saved![/green]")
            console.print(f"  Host: {data['proxmox_host']}")
            console.print(f"  User: {data['proxmox_user']}")
            
            if connection_ok:
                console.print("\n[green]✓ Connection verified![/green]")
                console.print("\n[yellow]Ready to:[/yellow]")
                console.print("  • Create VMs with 'create vm'")
                console.print("  • View configuration with 'show config'")
            else:
                console.print("\n[yellow]Note: Connection test failed but configuration saved.[/yellow]")
                console.print("You can run 'setup proxmox' again to update the settings.")
            
        elif wizard_name == "quick_vm_setup":
            # Map size to actual resources
            size_map = {
                "small": {"cores": 2, "memory": 4096, "disk": 20},
                "medium": {"cores": 4, "memory": 8192, "disk": 50},
                "large": {"cores": 8, "memory": 16384, "disk": 100}
            }
            
            resources = size_map.get(data['vm_size'], size_map['medium'])
            
            console.print(f"\n[yellow]Creating VM '{data['vm_name']}' with:[/yellow]")
            console.print(f"  • Type: {data['vm_type']}")
            console.print(f"  • Resources: {resources['cores']} cores, {resources['memory']}MB RAM, {resources['disk']}GB disk")
            
            # Here you would call MCP tools to create the VM
            # result = await mcp_client.call_tool("create_vm", {
            #     "name": data['vm_name'],
            #     "type": data['vm_type'],
            #     **resources
            # })
    
    async def _handle_ai_interaction(self, user_input: str, mcp_client) -> None:
        """Handle normal AI interaction (non-wizard)."""
        # Create system prompt
        system_prompt = self._create_system_prompt(list(mcp_client.tools.values()))
        
        # Add wizard awareness to system prompt
        system_prompt += """

You can also help users with configuration wizards. If a user wants to:
- Set up or configure Proxmox: suggest they type 'setup proxmox'
- Create a new VM quickly: suggest they type 'create vm'
- See current configuration: suggest they type 'show config'

These commands will start interactive wizards to guide them through the process."""
        
        console.print()  # New line before AI response
        
        try:
            # Get AI response with loading status
            with console.status("[bold blue]AI is thinking...[/bold blue]", spinner="dots"):
                response = await asyncio.to_thread(
                    self._get_ai_response, system_prompt, user_input
                )
            
            # Print the actual response
            console.print("[bold blue]AI:[/bold blue] ", end="")
            
            # Check for tool calls
            tool_calls = self._extract_tool_calls(response)
            
            if tool_calls:
                # Print the text before the JSON block
                console.print(response.split("```json")[0].strip())
                
                for tool_call in tool_calls:
                    tool_name = tool_call.get("name")
                    tool_args = tool_call.get("arguments", {})
                    
                    console.print(f"\n[dim]Calling tool: {tool_name}[/dim]")
                    
                    try:
                        result = await mcp_client.call_tool(tool_name, tool_args)
                        console.print(f"[green]Tool result: {result}[/green]")
                    except Exception as e:
                        console.print(f"[red]Error calling tool: {e}[/red]")
            else:
                console.print(response)
                
        except Exception as e:
            console.print(f"[red]Error getting AI response: {e}[/red]")
            console.print("[yellow]Please check your Ollama connection and try again.[/yellow]")
    
    async def _show_config(self) -> None:
        """Show current Proxmox configuration."""
        # Check if we have a configuration
        profile = await self.profile_manager.get_profile("main")
        
        if not profile:
            console.print("\n[yellow]No Proxmox configuration found.[/yellow]")
            console.print("Use 'setup proxmox' to configure your connection.")
            return
        
        console.print("\n[bold]Current Proxmox Configuration:[/bold]")
        console.print(f"  Host: [cyan]{profile.get('PROXMOX_HOST', 'Not set')}[/cyan]")
        console.print(f"  User: [cyan]{profile.get('PROXMOX_USER', 'Not set')}[/cyan]")
        console.print(f"  Password: [cyan]{'*' * 8 if profile.get('PROXMOX_PASSWORD') else 'Not set'}[/cyan]")
        console.print(f"  Verify SSL: [cyan]{profile.get('PROXMOX_VERIFY_SSL', 'false')}[/cyan]")
        
        # Show if it matches current env
        if Config.PROXMOX_HOST == profile.get('PROXMOX_HOST'):
            console.print("\n[green]✓ Configuration is active[/green]")
        else:
            console.print("\n[yellow]⚠ Configuration not active in current session[/yellow]")
            console.print("  Restart the agent to use updated configuration.")
    
    async def _test_connection(self) -> None:
        """Test current Proxmox connection."""
        # Check if we have a configuration
        profile = await self.profile_manager.get_profile("main")
        
        if not profile:
            console.print("\n[yellow]No Proxmox configuration found.[/yellow]")
            console.print("Use 'setup proxmox' to configure your connection.")
            return
        
        # Test the connection
        await ProxmoxConnectionTest.test_and_display(
            profile.get('PROXMOX_HOST'),
            profile.get('PROXMOX_USER'),
            profile.get('PROXMOX_PASSWORD'),
            profile.get('PROXMOX_VERIFY_SSL', 'false')
        )


async def main():
    """Main entry point."""
    agent = WebSocketAIAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())