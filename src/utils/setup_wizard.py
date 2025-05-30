"""
Setup wizard for collecting configuration data interactively.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import print as rprint
import aiofiles
from dotenv import set_key

console = Console()


class SetupWizard:
    """Interactive setup wizard for MCP configuration."""
    
    def __init__(self, env_path: str = ".env"):
        self.env_path = Path(env_path)
        self.config: Dict[str, Any] = {}
        self.wizard_steps = {
            "proxmox": self._collect_proxmox_config,
            "ollama": self._collect_ollama_config,
            "ansible": self._collect_ansible_config,
            "advanced": self._collect_advanced_config
        }
    
    async def run(self, sections: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run the setup wizard for specified sections or all sections."""
        if sections is None:
            sections = list(self.wizard_steps.keys())
        
        console.print(Panel.fit(
            "[bold cyan]MCP Setup Wizard[/bold cyan]\n"
            "This wizard will help you configure your MCP server.",
            title="Welcome"
        ))
        
        # Check if .env exists and offer to backup
        if self.env_path.exists():
            backup = Confirm.ask(
                f"\n[yellow].env file already exists. Create backup?[/yellow]",
                default=True
            )
            if backup:
                backup_path = self.env_path.with_suffix('.env.backup')
                import shutil
                shutil.copy(self.env_path, backup_path)
                console.print(f"[green]Backup created: {backup_path}[/green]")
        
        # Run selected wizard sections
        for section in sections:
            if section in self.wizard_steps:
                console.print(f"\n[bold]Configuring {section.title()}[/bold]")
                await self.wizard_steps[section]()
        
        # Show summary
        await self._show_summary()
        
        # Save configuration
        if Confirm.ask("\n[bold]Save configuration?[/bold]", default=True):
            await self._save_config()
            console.print("[green]Configuration saved successfully![/green]")
        
        return self.config
    
    async def _collect_proxmox_config(self) -> None:
        """Collect Proxmox configuration."""
        console.print("\n[cyan]Proxmox is used for VM management and infrastructure discovery.[/cyan]")
        
        # Basic connection info
        self.config["PROXMOX_HOST"] = Prompt.ask(
            "Proxmox host/IP",
            default="192.168.10.200"
        )
        
        self.config["PROXMOX_USER"] = Prompt.ask(
            "Proxmox username",
            default="root@pam"
        )
        
        self.config["PROXMOX_PASSWORD"] = Prompt.ask(
            "Proxmox password",
            password=True
        )
        
        self.config["PROXMOX_VERIFY_SSL"] = str(
            Confirm.ask("Verify SSL certificates?", default=False)
        ).lower()
        
        # Template configuration
        if Confirm.ask("\nConfigure VM template settings?", default=True):
            self.config["TEMPLATE_VM_ID"] = Prompt.ask(
                "Template VM ID",
                default="9000"
            )
            
            self.config["TEMPLATE_VM_NAME"] = Prompt.ask(
                "Template VM name",
                default="ubuntu-cloud-template"
            )
            
            self.config["DEFAULT_VM_USER"] = Prompt.ask(
                "Default VM user",
                default="ansible-admin"
            )
    
    async def _collect_ollama_config(self) -> None:
        """Collect Ollama configuration."""
        console.print("\n[cyan]Ollama is used for AI agent capabilities.[/cyan]")
        
        # Check for WSL
        is_wsl = Confirm.ask("Are you running in WSL?", default=False)
        
        if is_wsl:
            console.print("[yellow]For WSL, use your Windows host IP address.[/yellow]")
            default_host = "http://192.168.1.100:11434"
        else:
            default_host = "http://localhost:11434"
        
        self.config["OLLAMA_HOST"] = Prompt.ask(
            "Ollama host URL",
            default=default_host
        )
        
        # Model selection
        console.print("\n[cyan]Common Ollama models:[/cyan]")
        models = [
            ("llama3.2:3b", "Small, fast model (3B parameters)"),
            ("llama3.2:7b", "Medium model with better quality"),
            ("mistral:7b", "Good general purpose model"),
            ("codellama:7b", "Optimized for code tasks"),
            ("custom", "Enter custom model name")
        ]
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Model", style="cyan")
        table.add_column("Description")
        
        for i, (model, desc) in enumerate(models[:-1], 1):
            table.add_row(f"{i}. {model}", desc)
        table.add_row("5. custom", "Enter custom model name")
        
        console.print(table)
        
        choice = Prompt.ask(
            "Select model",
            choices=["1", "2", "3", "4", "5"],
            default="1"
        )
        
        if choice == "5":
            self.config["OLLAMA_MODEL"] = Prompt.ask("Enter custom model name")
        else:
            self.config["OLLAMA_MODEL"] = models[int(choice) - 1][0]
    
    async def _collect_ansible_config(self) -> None:
        """Collect Ansible configuration."""
        console.print("\n[cyan]Ansible is used for server configuration and automation.[/cyan]")
        
        self.config["ANSIBLE_HOST_KEY_CHECKING"] = str(
            Confirm.ask("Enable SSH host key checking?", default=False)
        ).lower()
        
        self.config["ANSIBLE_INVENTORY_PATH"] = Prompt.ask(
            "Ansible inventory path",
            default="./inventory/hosts.yml"
        )
    
    async def _collect_advanced_config(self) -> None:
        """Collect advanced configuration."""
        console.print("\n[cyan]Advanced settings for development and monitoring.[/cyan]")
        
        self.config["DEBUG"] = str(
            Confirm.ask("Enable debug mode?", default=False)
        ).lower()
        
        self.config["LOG_LEVEL"] = Prompt.ask(
            "Log level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            default="INFO"
        )
        
        self.config["INVENTORY_STALENESS_HOURS"] = Prompt.ask(
            "Inventory refresh interval (hours)",
            default="10"
        )
        
        self.config["INVENTORY_PATH"] = Prompt.ask(
            "Inventory storage path",
            default="./inventory"
        )
    
    async def _show_summary(self) -> None:
        """Show configuration summary."""
        console.print("\n[bold]Configuration Summary:[/bold]")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Setting", style="cyan", width=30)
        table.add_column("Value", width=50)
        
        for key, value in sorted(self.config.items()):
            # Mask sensitive values
            display_value = value
            if "PASSWORD" in key and value:
                display_value = "*" * min(len(value), 8)
            
            table.add_row(key, display_value)
        
        console.print(table)
    
    async def _save_config(self) -> None:
        """Save configuration to .env file."""
        # Create .env if it doesn't exist
        if not self.env_path.exists():
            self.env_path.touch()
        
        # Write each config value
        for key, value in self.config.items():
            set_key(str(self.env_path), key, value)
        
        # Also save a JSON backup for reference
        json_backup = self.env_path.with_suffix('.env.json')
        async with aiofiles.open(json_backup, 'w') as f:
            # Create safe version without passwords
            safe_config = self.config.copy()
            for key in safe_config:
                if "PASSWORD" in key:
                    safe_config[key] = "***HIDDEN***"
            
            await f.write(json.dumps(safe_config, indent=2))


class WizardFlow:
    """Wizard flow manager for chat-based interactions."""
    
    def __init__(self):
        self.current_step = None
        self.collected_data = {}
        self.flow_definition = {}
    
    def define_flow(self, name: str, steps: List[Dict[str, Any]]) -> None:
        """Define a wizard flow with steps."""
        self.flow_definition[name] = {
            "steps": steps,
            "current_index": 0,
            "data": {}
        }
    
    def start_flow(self, name: str) -> Dict[str, Any]:
        """Start a wizard flow and return the first step."""
        if name not in self.flow_definition:
            raise ValueError(f"Flow '{name}' not defined")
        
        flow = self.flow_definition[name]
        flow["current_index"] = 0
        flow["data"] = {}
        
        return self._get_current_step(name)
    
    def process_response(self, flow_name: str, response: str) -> Tuple[bool, Dict[str, Any]]:
        """Process user response and return (is_complete, next_step_or_result)."""
        flow = self.flow_definition[flow_name]
        current_step = flow["steps"][flow["current_index"]]
        
        # Validate response if validator provided
        if "validator" in current_step:
            is_valid, error_msg = current_step["validator"](response)
            if not is_valid:
                return False, {
                    "type": "error",
                    "message": error_msg,
                    "retry_prompt": current_step["prompt"]
                }
        
        # Store the response
        flow["data"][current_step["key"]] = response
        
        # Move to next step
        flow["current_index"] += 1
        
        # Check if complete
        if flow["current_index"] >= len(flow["steps"]):
            return True, {
                "type": "complete",
                "data": flow["data"]
            }
        
        # Return next step
        return False, self._get_current_step(flow_name)
    
    def _get_current_step(self, flow_name: str) -> Dict[str, Any]:
        """Get the current step details."""
        flow = self.flow_definition[flow_name]
        step = flow["steps"][flow["current_index"]]
        
        return {
            "type": "prompt",
            "prompt": step["prompt"],
            "key": step["key"],
            "options": step.get("options"),
            "default": step.get("default"),
            "input_type": step.get("input_type", "text")
        }


# Example wizard flow definitions
PROXMOX_WIZARD_FLOW = [
    {
        "key": "proxmox_host",
        "prompt": "What is your Proxmox server's IP address or hostname?",
        "default": "192.168.10.200",
        "validator": lambda x: (True, "") if x else (False, "Host cannot be empty")
    },
    {
        "key": "proxmox_user",
        "prompt": "What is your Proxmox username?",
        "default": "root@pam",
        "validator": lambda x: (True, "") if "@" in x else (False, "Username must include realm (e.g., root@pam)")
    },
    {
        "key": "proxmox_password",
        "prompt": "What is your Proxmox password?",
        "input_type": "password",
        "validator": lambda x: (True, "") if x else (False, "Password cannot be empty")
    },
    {
        "key": "verify_ssl",
        "prompt": "Do you want to verify SSL certificates? (yes/no)",
        "default": "no",
        "options": ["yes", "no"],
        "validator": lambda x: (True, "") if x.lower() in ["yes", "no"] else (False, "Please answer yes or no")
    }
]


if __name__ == "__main__":
    # Test the wizard
    async def test_wizard():
        wizard = SetupWizard()
        await wizard.run(["proxmox", "ollama"])
    
    asyncio.run(test_wizard())