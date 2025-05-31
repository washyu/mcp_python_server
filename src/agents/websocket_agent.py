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
from rich.prompt import Prompt, Confirm
from config import Config
from src.client.websocket_client import MCPWebSocketClient
from src.utils.setup_wizard import WizardFlow, PROXMOX_WIZARD_FLOW
from src.utils.profile_manager import ProfileManager
from src.utils.proxmox_tools import ProxmoxConnectionTest
from src.tools.proxmox_discovery import handle_proxmox_tool

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
            f"[bold cyan]WebSocket AI Agent with Proxmox Discovery[/bold cyan]\n"
            f"Model: {self.model}\n"
            f"Ollama Host: {Config.OLLAMA_HOST}\n"
            f"MCP Server: {self.mcp_uri}\n\n"
            f"[yellow]Setup Commands:[/yellow]\n"
            f"  • 'setup proxmox' - Configure Proxmox connection\n"
            f"  • 'show config' - Show current configuration\n"
            f"  • 'test connection' - Test Proxmox connection\n\n"
            f"[green]Smart Discovery & Hardware Intelligence:[/green]\n"
            f"  • Basic: 'running vms' | 'mysql servers' | 'vm #203'\n"
            f"  • Hardware: 'discover hardware' | 'show gpus'\n"
            f"  • General: 'list nodes' | 'storage pools' | 'templates'\n\n"
            f"[cyan]AI-Powered Deployment:[/cyan]\n"
            f"  • Suggestions: 'suggest deployment for ai_training'\n"
            f"  • Optimization: 'optimize vm placement'\n"
            f"  • Visualization: 'generate diagram' | 'topology chart'\n"
            f"  • Intelligence: GPU-aware, resource-optimized\n\n"
            f"[yellow]Other:[/yellow] 'create vm' | 'quit'",
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
        
        elif "create token" in input_lower or "generate token" in input_lower:
            await self._create_api_token()
            return True
        
        # Proxmox discovery commands (enhanced natural language support)
        elif any(pattern in input_lower for pattern in [
            "list nodes", "show nodes", "nodes on", "proxmox nodes", "cluster nodes"
        ]):
            await self._run_discovery_tool("proxmox_list_nodes")
            return True
        
        elif any(pattern in input_lower for pattern in [
            "list vms", "show vms", "list vm", "show vm", "virtual machines", 
            "vms on", "vm on", "list all vm", "show all vm", "all virtual machine",
            "running vm", "stopped vm", "running vms", "stopped vms", "vm with", 
            "vms with", "find vm", "search vm", "vm id", "server with", "find server",
            "show me", "what is", "windows vm", "ubuntu vm", "linux vm", "mysql server",
            "nextcloud server", "jenkins server", "docker server", "cores", "memory",
            "gb", "cpu"
        ]):
            # Parse comprehensive filters from natural language
            filters = self._parse_vm_filters(user_input)
            
            # Add helpful context for unusual queries
            if not filters and any(term in user_input.lower() for term in [
                "bob", "skynet", "hal", "jarvis", "toaster", "refrigerator", 
                "bicycle", "amiga", "commodore", "dos", "os/2", "mainframe"
            ]):
                console.print("[yellow]💡 Tip: That system type isn't in our homelab! Try:[/yellow]")
                console.print("  • 'ubuntu servers' | 'windows vms' | 'mysql servers'")
                console.print("  • 'running vms' | 'stopped machines' | 'vm 203'")
                return True
            
            await self._run_discovery_tool("proxmox_list_vms", filters)
            return True
        
        elif any(pattern in input_lower for pattern in [
            "list storage", "show storage", "storage pools", "storage on", "disk storage"
        ]):
            await self._run_discovery_tool("proxmox_list_storage")
            return True
        
        elif any(pattern in input_lower for pattern in [
            "list templates", "show templates", "vm templates", "templates on", "template"
        ]):
            await self._run_discovery_tool("proxmox_list_templates")
            return True
        
        elif any(pattern in input_lower for pattern in [
            "discovery status", "inventory status", "status", "discovery", "inventory"
        ]):
            await self._run_discovery_tool("proxmox_discovery_status")
            return True
        
        elif any(pattern in input_lower for pattern in [
            "refresh inventory", "refresh discovery", "refresh", "scan proxmox", "update inventory"
        ]):
            await self._run_discovery_tool("proxmox_refresh_inventory")
            return True
        
        elif any(pattern in input_lower for pattern in [
            "discover hardware", "hardware discovery", "show hardware", "list hardware", 
            "gpu discovery", "show gpus", "list gpus", "cpu details", "storage details"
        ]):
            # Parse node name if specified
            node_name = None
            if "node" in input_lower:
                import re
                match = re.search(r"node\s+([a-zA-Z0-9\-_]+)", input_lower)
                if match:
                    node_name = match.group(1)
            
            arguments = {"node_name": node_name} if node_name else {}
            await self._run_discovery_tool("proxmox_discover_hardware", arguments)
            return True
        
        elif any(pattern in input_lower for pattern in [
            "suggest deployment", "deployment suggestion", "where to deploy", "best node for",
            "deploy ai", "deploy database", "deploy web", "deploy compute", "ai training",
            "training server", "ollama server"
        ]):
            # Parse workload type
            workload_type = "general"  # default
            if any(term in input_lower for term in ["ai", "training", "ollama", "ml", "machine learning"]):
                workload_type = "ai_training"
            elif any(term in input_lower for term in ["database", "mysql", "postgres", "db"]):
                workload_type = "database"
            elif any(term in input_lower for term in ["web", "nginx", "apache", "http"]):
                workload_type = "web_server"
            elif any(term in input_lower for term in ["compute", "calculation", "processing"]):
                workload_type = "compute"
            elif any(term in input_lower for term in ["storage", "backup", "file"]):
                workload_type = "storage"
            
            arguments = {"workload_type": workload_type}
            await self._run_discovery_tool("proxmox_suggest_deployment", arguments)
            return True
        
        elif any(pattern in input_lower for pattern in [
            "optimize placement", "vm optimization", "optimize vms", "placement optimization",
            "migration suggestions", "load balancing", "resource optimization"
        ]):
            await self._run_discovery_tool("proxmox_optimize_placement")
            return True
        
        elif any(pattern in input_lower for pattern in [
            "generate diagram", "infrastructure diagram", "topology diagram", "show diagram",
            "visual diagram", "infrastructure chart", "resource chart", "topology chart"
        ]):
            # Determine diagram type
            diagram_type = "full"  # default
            if any(term in input_lower for term in ["topology", "infrastructure"]):
                diagram_type = "topology"
            elif any(term in input_lower for term in ["resource", "utilization"]):
                diagram_type = "resources"
            
            arguments = {"format": diagram_type}
            await self._run_discovery_tool("proxmox_generate_diagram", arguments)
            return True
        
        return False
    
    async def _process_wizard_results(self, wizard_name: str, data: Dict[str, Any], mcp_client: Any = None) -> None:
        """Process completed wizard results."""
        if wizard_name == "proxmox_setup":
            # Test the connection first (and possibly create token)
            connection_ok, api_token = await ProxmoxConnectionTest.test_and_display(
                data["proxmox_host"],
                data["proxmox_user"],
                data["proxmox_password"],
                data["verify_ssl"],
                offer_token_creation=True
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
            
            # Add API token if one was created
            if api_token:
                config["PROXMOX_API_TOKEN"] = api_token
                console.print("\n[green]✓ API token added to configuration![/green]")
            
            # Save and activate the profile
            await self.profile_manager.create_profile(profile_name, config)
            await self.profile_manager.set_active_profile(profile_name)
            await self.profile_manager.export_to_env(profile_name)
            
            console.print(f"\n[green]✓ Proxmox configuration saved![/green]")
            console.print(f"  Host: {data['proxmox_host']}")
            console.print(f"  User: {data['proxmox_user']}")
            
            if connection_ok:
                if api_token:
                    console.print("\n[green]✓ Using API token for authentication[/green]")
                    console.print("[dim]This provides better reliability with no timeouts.[/dim]")
                else:
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
        
        # Test the connection (don't offer token creation here)
        await ProxmoxConnectionTest.test_and_display(
            profile.get('PROXMOX_HOST'),
            profile.get('PROXMOX_USER'),
            profile.get('PROXMOX_PASSWORD'),
            profile.get('PROXMOX_VERIFY_SSL', 'false'),
            offer_token_creation=False
        )
    
    async def _create_api_token(self) -> None:
        """Create a Proxmox API token for MCP use."""
        # Check if we have a configuration
        profile = await self.profile_manager.get_profile("main")
        
        if not profile:
            console.print("\n[yellow]No Proxmox configuration found.[/yellow]")
            console.print("Use 'setup proxmox' to configure your connection first.")
            return
        
        # Check if already using token
        if profile.get('PROXMOX_API_TOKEN'):
            console.print("\n[yellow]Already using API token authentication.[/yellow]")
            if not Confirm.ask("Create a new token anyway?", default=False):
                return
        
        # Create token
        token = await ProxmoxConnectionTest.create_mcp_token(
            profile.get('PROXMOX_HOST'),
            profile.get('PROXMOX_USER'),
            profile.get('PROXMOX_PASSWORD'),
            profile.get('PROXMOX_VERIFY_SSL', 'false')
        )
        
        if token:
            # Update profile with token
            profile['PROXMOX_API_TOKEN'] = token
            await self.profile_manager.update_profile("main", profile)
            await self.profile_manager.export_to_env("main")
            
            console.print("\n[green]✓ Token saved to configuration![/green]")
            console.print("[yellow]Restart the agent to use the new token.[/yellow]")
    
    async def _run_discovery_tool(self, tool_name: str, arguments: dict = None) -> None:
        """Run a Proxmox discovery tool directly."""
        try:
            if arguments:
                console.print(f"\n[dim]Running {tool_name} with filters...[/dim]")
            else:
                console.print(f"\n[dim]Running {tool_name}...[/dim]")
            
            # Call the discovery tool directly (bypassing MCP server)
            result = await handle_proxmox_tool(tool_name, arguments or {})
            
            if result:
                # Display the result
                for content in result:
                    if hasattr(content, 'text'):
                        console.print(content.text)
                    else:
                        console.print(str(content))
            else:
                console.print("[yellow]No results returned.[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Error running discovery tool: {e}[/red]")
            console.print("\n[yellow]Make sure you have configured Proxmox credentials first:[/yellow]")
            console.print("  [cyan]setup proxmox[/cyan]")
    
    def _parse_vm_filters(self, user_input: str) -> dict:
        """Parse natural language input to extract VM filters."""
        import re
        input_lower = user_input.lower()
        filters = {}
        
        # Status filters - handle multiple status types and edge cases
        status_patterns = {
            "running": r"\brunning\b",
            "stopped": r"\bstopped\b", 
            "paused": r"\bpaused\b|\bsuspended\b"
        }
        
        for status_name, pattern in status_patterns.items():
            if re.search(pattern, input_lower):
                filters["status"] = status_name
                break
        
        # ID filter - look for patterns like "id 44", "id of 44", "with id 44"
        id_patterns = [
            r"id\s+(\d+)",
            r"id\s+of\s+(\d+)", 
            r"with\s+id\s+(\d+)",
            r"vm\s+(\d{1,4})",  # VM IDs are typically 1-4 digits
            r"(?<!windows\s)(?<!server\s)server\s+(\d{1,4})",  # Avoid "windows server 2022"
            r"machine\s+(\d{1,4})",
            r"#(\d{1,4})"  # hashtag notation
        ]
        for pattern in id_patterns:
            match = re.search(pattern, input_lower)
            if match:
                vm_id = match.group(1)
                # Validate ID is reasonable (1-9999)
                try:
                    id_int = int(vm_id)
                    if 1 <= id_int <= 9999:
                        filters["id"] = id_int
                    break
                except ValueError:
                    continue  # Skip invalid IDs
        
        # Name filters - look for specific server names with improved matching
        name_patterns = [
            # Service-specific patterns (prioritize these)
            r"(nextcloud|jenkins|mysql|database|web|docker|nginx|apache|ollama|production|dev|test)\s*server",
            r"(nextcloud|jenkins|mysql|database|web|docker|nginx|apache|ollama|production|dev|test)\s*machine",
            r"(nextcloud|jenkins|mysql|database|web|docker|nginx|apache|ollama)",
            # Environment patterns
            r"(production|development|staging|test)\s*(server|machine|vm|environment)",
            r"(prod|dev|stage|test)\s*(server|machine|vm)",
            # Generic patterns with better character support
            r"named?\s+([a-zA-Z0-9\-_\.]+)",
            r"called\s+([a-zA-Z0-9\-_\.]+)",
            # Quoted names
            r'"([a-zA-Z0-9\-_\.\s]+)"',
            r"'([a-zA-Z0-9\-_\.\s]+)'"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, input_lower)
            if match and match.group(1) not in ['of', 'the', 'a', 'an', 'with', 'server', 'machine', 'vm']:
                filters["name"] = match.group(1).strip()
                break
        
        # OS/Distribution filters - only apply if no name filter found for service keywords
        service_keywords = ["mysql", "nextcloud", "docker", "production", "development", "dev", "test"]
        should_apply_os_filter = True
        
        # If we already found a name filter that matches a service, don't override with OS
        if "name" in filters and any(keyword in filters["name"] for keyword in service_keywords):
            should_apply_os_filter = False
        
        if should_apply_os_filter:
            os_patterns = {
                # Specific version patterns (higher priority)
                "ubuntu 22.04": r"ubuntu\s*22\.?04|jammy|22\.04",
                "ubuntu 20.04": r"ubuntu\s*20\.?04|focal|20\.04",
                "ubuntu 18.04": r"ubuntu\s*18\.?04|bionic|18\.04",
                "windows server 2022": r"windows?\s*(server\s*)?2022|w2k22|ws2022",
                "windows server 2019": r"windows?\s*(server\s*)?2019|w2k19|ws2019",
                # General OS patterns
                "windows": r"windows|win(?!g)|w2k",
                "ubuntu": r"ubuntu(?!\s*\d)",  # Ubuntu but not followed by version
                "debian": r"debian",
                "centos": r"centos|rhel|redhat|rocky|alma",
                "linux": r"linux(?!\s*(mint|lite))",  # Linux but exclude specific distros
                # Service-based OS detection (only if no name match)
                "nextcloud": r"nextcloud",
                "mysql": r"mysql|mariadb",
                "docker": r"docker|container",
                # Application patterns
                "web": r"web\s*server|nginx|apache|httpd",
                "database": r"(?<!mysql\s)database|db\s*server|postgres|mongodb"
            }
            
            for os_name, pattern in os_patterns.items():
                if re.search(pattern, input_lower):
                    filters["os"] = os_name
                    break
        
        # Memory filters - support decimal values and multiple units
        memory_patterns = [
            # GB patterns with decimal support
            r"with\s+([0-9.]+)\s*gb",
            r"more\s+than\s+([0-9.]+)\s*gb",
            r"at\s+least\s+([0-9.]+)\s*gb",
            r"([0-9.]+)\s*gb\s+memory",
            r"([0-9.]+)\s*gb\s+ram",
            r"over\s+([0-9.]+)\s*gb",
            r"above\s+([0-9.]+)\s*gb",
            # MB patterns
            r"with\s+(\d+)\s*mb",
            r"([0-9.]+)\s*mb\s+memory",
            # Exact memory
            r"exactly\s+([0-9.]+)\s*gb"
        ]
        for pattern in memory_patterns:
            match = re.search(pattern, input_lower)
            if match:
                try:
                    memory_value = float(match.group(1))
                    # Convert to MB based on unit detection
                    if "mb" in pattern:
                        filters["min_memory"] = int(memory_value)  # Already in MB
                    else:
                        filters["min_memory"] = int(memory_value * 1024)  # GB to MB
                    break
                except ValueError:
                    continue  # Skip invalid memory values
        
        # CPU filters - support various CPU terminology and edge cases
        cpu_patterns = [
            r"with\s+([0-9.]+)\s+cores?",
            r"with\s+([0-9.]+)\s+cpus?",
            r"more\s+than\s+([0-9.]+)\s+cores?",
            r"at\s+least\s+([0-9.]+)\s+cores?",
            r"([0-9.]+)\s+cores?",
            r"([0-9.]+)\s+cpus?",
            r"over\s+([0-9.]+)\s+cores?",
            r"above\s+([0-9.]+)\s+cores?",
            # Alternative terminology
            r"([0-9.]+)\s+processors?",
            r"([0-9.]+)\s+vcpus?",
            # Special cases
            r"single\s+core",  # matches to 1
            r"dual\s+core",   # matches to 2
            r"quad\s+core",   # matches to 4
            r"multi\s+core"   # matches to 2+ (we'll use 2)
        ]
        
        for pattern in cpu_patterns:
            match = re.search(pattern, input_lower)
            if match:
                try:
                    if "single" in pattern:
                        filters["min_cpu"] = 1
                    elif "dual" in pattern:
                        filters["min_cpu"] = 2
                    elif "quad" in pattern:
                        filters["min_cpu"] = 4
                    elif "multi" in pattern:
                        filters["min_cpu"] = 2
                    else:
                        cpu_value = float(match.group(1))
                        # Only accept reasonable CPU values (0.1 to 64)
                        if 0.1 <= cpu_value <= 64:
                            filters["min_cpu"] = int(cpu_value)  # Round down for minimums
                    break
                except (ValueError, IndexError):
                    continue  # Skip invalid CPU values
        
        # Handle complex queries and provide warnings for conflicting filters
        self._validate_and_warn_filters(filters, user_input)
        
        return filters
    
    def _validate_and_warn_filters(self, filters: dict, user_input: str) -> None:
        """Validate filters and warn about potential issues."""
        # Check for conflicting OS filters
        if "os" in filters:
            input_lower = user_input.lower()
            
            # Detect multiple OS mentions for potential conflicts
            os_keywords = ["windows", "ubuntu", "debian", "centos", "linux"]
            mentioned_os = [os for os in os_keywords if os in input_lower]
            
            if len(mentioned_os) > 1:
                # User mentioned multiple OS types, we already picked the best match
                # This is just for validation - no action needed
                pass
        
        # Validate memory ranges
        if "min_memory" in filters:
            if filters["min_memory"] <= 0:
                filters.pop("min_memory")  # Remove invalid memory filter
            elif filters["min_memory"] > 65536:  # More than 64GB seems excessive
                filters["min_memory"] = 65536  # Cap at reasonable limit
        
        # Validate CPU ranges  
        if "min_cpu" in filters:
            if filters["min_cpu"] <= 0:
                filters.pop("min_cpu")  # Remove invalid CPU filter
            elif filters["min_cpu"] > 32:  # More than 32 cores seems excessive for homelab
                filters["min_cpu"] = 32  # Cap at reasonable limit


async def main():
    """Main entry point."""
    agent = WebSocketAIAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())