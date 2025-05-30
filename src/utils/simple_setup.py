"""
Simplified setup wizard for single Proxmox server configuration.
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from dotenv import set_key
import aiofiles
import json

console = Console()


class SimpleSetup:
    """Simple setup wizard for single server configuration."""
    
    def __init__(self, env_path: str = ".env"):
        self.env_path = Path(env_path)
        self.profile_dir = Path("./profiles")
        self.profile_dir.mkdir(exist_ok=True)
    
    async def check_existing_config(self) -> Optional[Dict[str, Any]]:
        """Check if configuration already exists."""
        # Check profile
        profile_file = self.profile_dir / "profiles.json"
        if profile_file.exists():
            async with aiofiles.open(profile_file, 'r') as f:
                content = await f.read()
                profiles = json.loads(content) if content else {}
                return profiles.get("main")
        return None
    
    async def run(self) -> Dict[str, Any]:
        """Run the simplified setup wizard."""
        console.print(Panel.fit(
            "[bold cyan]Proxmox Server Setup[/bold cyan]\n"
            "This wizard will configure your connection to Proxmox.",
            title="Welcome"
        ))
        
        # Check for existing configuration
        existing = await self.check_existing_config()
        if existing:
            console.print("\n[yellow]Existing configuration found:[/yellow]")
            console.print(f"  Host: {existing.get('PROXMOX_HOST')}")
            console.print(f"  User: {existing.get('PROXMOX_USER')}")
            
            if not Confirm.ask("\nDo you want to reconfigure?", default=False):
                console.print("[green]Using existing configuration.[/green]")
                return existing
        
        # Collect configuration
        config = {}
        
        console.print("\n[bold]Proxmox Connection Details[/bold]")
        
        config["PROXMOX_HOST"] = Prompt.ask(
            "Proxmox server IP/hostname",
            default=existing.get("PROXMOX_HOST", "192.168.10.200") if existing else "192.168.10.200"
        )
        
        config["PROXMOX_USER"] = Prompt.ask(
            "Username",
            default=existing.get("PROXMOX_USER", "root@pam") if existing else "root@pam"
        )
        
        config["PROXMOX_PASSWORD"] = Prompt.ask(
            "Password",
            password=True
        )
        
        config["PROXMOX_VERIFY_SSL"] = str(
            Confirm.ask("Verify SSL certificate?", default=False)
        ).lower()
        
        # Template configuration
        if Confirm.ask("\nConfigure VM template settings?", default=True):
            console.print("\n[bold]VM Template Configuration[/bold]")
            
            config["TEMPLATE_VM_ID"] = Prompt.ask(
                "Template VM ID",
                default=existing.get("TEMPLATE_VM_ID", "9000") if existing else "9000"
            )
            
            config["TEMPLATE_VM_NAME"] = Prompt.ask(
                "Template name",
                default=existing.get("TEMPLATE_VM_NAME", "ubuntu-cloud-template") if existing else "ubuntu-cloud-template"
            )
            
            config["DEFAULT_VM_USER"] = Prompt.ask(
                "Default VM username",
                default=existing.get("DEFAULT_VM_USER", "ansible-admin") if existing else "ansible-admin"
            )
        
        # Save configuration
        console.print("\n[bold]Saving Configuration[/bold]")
        
        # Save to profile
        await self._save_profile(config)
        
        # Export to .env
        await self._export_to_env(config)
        
        console.print("\n[green]✓ Configuration saved successfully![/green]")
        console.print("\nYour Proxmox server is now configured and ready to use.")
        console.print("The MCP server will use these settings to manage your infrastructure.")
        
        return config
    
    async def _save_profile(self, config: Dict[str, Any]) -> None:
        """Save configuration to profile."""
        profile_file = self.profile_dir / "profiles.json"
        active_file = self.profile_dir / "active_profile.txt"
        
        # Save profile
        profiles = {"main": config}
        async with aiofiles.open(profile_file, 'w') as f:
            await f.write(json.dumps(profiles, indent=2))
        
        # Set as active
        async with aiofiles.open(active_file, 'w') as f:
            await f.write("main")
    
    async def _export_to_env(self, config: Dict[str, Any]) -> None:
        """Export configuration to .env file."""
        # Create .env if it doesn't exist
        if not self.env_path.exists():
            self.env_path.touch()
        
        # Write each config value
        for key, value in config.items():
            set_key(str(self.env_path), key, value)
    
    async def verify_connection(self) -> bool:
        """Verify Proxmox connection (placeholder for actual implementation)."""
        console.print("\n[yellow]In a complete implementation, this would:[/yellow]")
        console.print("  • Test connection to Proxmox API")
        console.print("  • Verify credentials")
        console.print("  • Check template VM exists")
        console.print("  • Display available resources")
        
        # This would call actual MCP tools
        # result = await mcp_client.call_tool("test_proxmox_connection")
        
        return True


async def main():
    """Run the simple setup."""
    setup = SimpleSetup()
    await setup.run()
    
    if Confirm.ask("\nTest Proxmox connection?", default=True):
        await setup.verify_connection()


if __name__ == "__main__":
    asyncio.run(main())