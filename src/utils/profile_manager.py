"""
Profile manager for handling multiple server configurations.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import aiofiles
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

console = Console()


class ProfileManager:
    """Manage multiple server profiles (Proxmox, Ansible, etc.)."""
    
    def __init__(self, profile_dir: str = "./profiles"):
        self.profile_dir = Path(profile_dir)
        self.profile_dir.mkdir(exist_ok=True)
        self.profiles_file = self.profile_dir / "profiles.json"
        self.active_profile_file = self.profile_dir / "active_profile.txt"
    
    async def load_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Load all saved profiles."""
        if not self.profiles_file.exists():
            return {}
        
        async with aiofiles.open(self.profiles_file, 'r') as f:
            content = await f.read()
            return json.loads(content) if content else {}
    
    async def save_profiles(self, profiles: Dict[str, Dict[str, Any]]) -> None:
        """Save profiles to disk."""
        async with aiofiles.open(self.profiles_file, 'w') as f:
            await f.write(json.dumps(profiles, indent=2))
    
    async def get_active_profile(self) -> Optional[str]:
        """Get the currently active profile name."""
        if not self.active_profile_file.exists():
            return None
        
        async with aiofiles.open(self.active_profile_file, 'r') as f:
            return (await f.read()).strip()
    
    async def set_active_profile(self, profile_name: str) -> None:
        """Set the active profile."""
        async with aiofiles.open(self.active_profile_file, 'w') as f:
            await f.write(profile_name)
    
    async def create_profile(self, name: str, config: Dict[str, Any]) -> None:
        """Create a new profile."""
        profiles = await self.load_profiles()
        profiles[name] = config
        await self.save_profiles(profiles)
    
    async def update_profile(self, name: str, config: Dict[str, Any]) -> None:
        """Update an existing profile."""
        profiles = await self.load_profiles()
        if name in profiles:
            profiles[name].update(config)
            await self.save_profiles(profiles)
    
    async def delete_profile(self, name: str) -> bool:
        """Delete a profile."""
        profiles = await self.load_profiles()
        if name in profiles:
            del profiles[name]
            await self.save_profiles(profiles)
            
            # If this was the active profile, clear it
            if await self.get_active_profile() == name:
                if self.active_profile_file.exists():
                    self.active_profile_file.unlink()
            
            return True
        return False
    
    async def list_profiles(self) -> List[str]:
        """List all profile names."""
        profiles = await self.load_profiles()
        return list(profiles.keys())
    
    async def get_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific profile configuration."""
        profiles = await self.load_profiles()
        return profiles.get(name)
    
    async def export_to_env(self, profile_name: str, env_path: str = ".env") -> bool:
        """Export a profile to .env format."""
        profile = await self.get_profile(profile_name)
        if not profile:
            return False
        
        env_path = Path(env_path)
        
        # Read existing .env to preserve non-profile settings
        existing_config = {}
        if env_path.exists():
            async with aiofiles.open(env_path, 'r') as f:
                for line in (await f.read()).splitlines():
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        existing_config[key] = value
        
        # Update with profile values
        existing_config.update(profile)
        
        # Write back
        async with aiofiles.open(env_path, 'w') as f:
            await f.write("# MCP Server Configuration\n")
            await f.write(f"# Active Profile: {profile_name}\n\n")
            
            for key, value in sorted(existing_config.items()):
                await f.write(f"{key}={value}\n")
        
        return True
    
    def display_profiles(self, profiles: Dict[str, Dict[str, Any]], active: Optional[str] = None) -> None:
        """Display profiles in a nice table."""
        if not profiles:
            console.print("[yellow]No profiles found.[/yellow]")
            return
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Profile", style="cyan")
        table.add_column("Proxmox Host")
        table.add_column("User")
        table.add_column("Status")
        
        for name, config in profiles.items():
            status = "[green]Active[/green]" if name == active else ""
            table.add_row(
                name,
                config.get("PROXMOX_HOST", "Not set"),
                config.get("PROXMOX_USER", "Not set"),
                status
            )
        
        console.print(table)


class ProfileWizard:
    """Wizard for managing server profiles."""
    
    def __init__(self):
        self.manager = ProfileManager()
    
    async def run(self) -> None:
        """Run the profile management wizard."""
        while True:
            console.print("\n[bold]Profile Management[/bold]")
            console.print("1. List profiles")
            console.print("2. Create new profile")
            console.print("3. Switch active profile")
            console.print("4. Edit profile")
            console.print("5. Delete profile")
            console.print("6. Export profile to .env")
            console.print("7. Exit")
            
            choice = Prompt.ask("Select option", choices=["1", "2", "3", "4", "5", "6", "7"])
            
            if choice == "1":
                await self._list_profiles()
            elif choice == "2":
                await self._create_profile()
            elif choice == "3":
                await self._switch_profile()
            elif choice == "4":
                await self._edit_profile()
            elif choice == "5":
                await self._delete_profile()
            elif choice == "6":
                await self._export_profile()
            elif choice == "7":
                break
    
    async def _list_profiles(self) -> None:
        """List all profiles."""
        profiles = await self.manager.load_profiles()
        active = await self.manager.get_active_profile()
        
        console.print("\n[bold]Server Profiles:[/bold]")
        self.manager.display_profiles(profiles, active)
    
    async def _create_profile(self) -> None:
        """Create a new profile."""
        name = Prompt.ask("\nProfile name")
        
        # Check if exists
        existing = await self.manager.get_profile(name)
        if existing:
            if not Confirm.ask(f"Profile '{name}' exists. Overwrite?"):
                return
        
        console.print(f"\n[cyan]Creating profile: {name}[/cyan]")
        
        config = {}
        
        # Proxmox settings
        if Confirm.ask("Configure Proxmox settings?", default=True):
            config["PROXMOX_HOST"] = Prompt.ask("Proxmox host", default="192.168.10.200")
            config["PROXMOX_USER"] = Prompt.ask("Proxmox user", default="root@pam")
            config["PROXMOX_PASSWORD"] = Prompt.ask("Proxmox password", password=True)
            config["PROXMOX_VERIFY_SSL"] = str(Confirm.ask("Verify SSL?", default=False)).lower()
        
        # Template settings
        if Confirm.ask("Configure template settings?", default=True):
            config["TEMPLATE_VM_ID"] = Prompt.ask("Template VM ID", default="9000")
            config["TEMPLATE_VM_NAME"] = Prompt.ask("Template name", default="ubuntu-cloud-template")
        
        await self.manager.create_profile(name, config)
        console.print(f"[green]Profile '{name}' created![/green]")
        
        if Confirm.ask("Set as active profile?", default=True):
            await self.manager.set_active_profile(name)
            console.print(f"[green]Profile '{name}' is now active.[/green]")
    
    async def _switch_profile(self) -> None:
        """Switch active profile."""
        profiles = await self.manager.list_profiles()
        if not profiles:
            console.print("[yellow]No profiles available.[/yellow]")
            return
        
        current = await self.manager.get_active_profile()
        console.print(f"\nCurrent active profile: [cyan]{current or 'None'}[/cyan]")
        console.print("\nAvailable profiles:")
        for i, name in enumerate(profiles, 1):
            console.print(f"  {i}. {name}")
        
        choice = Prompt.ask("Select profile", choices=[str(i) for i in range(1, len(profiles) + 1)])
        selected = profiles[int(choice) - 1]
        
        await self.manager.set_active_profile(selected)
        console.print(f"[green]Switched to profile '{selected}'[/green]")
        
        if Confirm.ask("Export to .env?", default=True):
            await self.manager.export_to_env(selected)
            console.print("[green]Profile exported to .env[/green]")
    
    async def _edit_profile(self) -> None:
        """Edit an existing profile."""
        profiles = await self.manager.list_profiles()
        if not profiles:
            console.print("[yellow]No profiles available.[/yellow]")
            return
        
        console.print("\nSelect profile to edit:")
        for i, name in enumerate(profiles, 1):
            console.print(f"  {i}. {name}")
        
        choice = Prompt.ask("Select profile", choices=[str(i) for i in range(1, len(profiles) + 1)])
        selected = profiles[int(choice) - 1]
        
        config = await self.manager.get_profile(selected)
        console.print(f"\n[cyan]Editing profile: {selected}[/cyan]")
        
        # Show current values and allow editing
        if "PROXMOX_HOST" in config:
            config["PROXMOX_HOST"] = Prompt.ask("Proxmox host", default=config["PROXMOX_HOST"])
        if "PROXMOX_USER" in config:
            config["PROXMOX_USER"] = Prompt.ask("Proxmox user", default=config["PROXMOX_USER"])
        
        if Confirm.ask("Update password?", default=False):
            config["PROXMOX_PASSWORD"] = Prompt.ask("New password", password=True)
        
        await self.manager.update_profile(selected, config)
        console.print(f"[green]Profile '{selected}' updated![/green]")
    
    async def _delete_profile(self) -> None:
        """Delete a profile."""
        profiles = await self.manager.list_profiles()
        if not profiles:
            console.print("[yellow]No profiles available.[/yellow]")
            return
        
        console.print("\nSelect profile to delete:")
        for i, name in enumerate(profiles, 1):
            console.print(f"  {i}. {name}")
        
        choice = Prompt.ask("Select profile", choices=[str(i) for i in range(1, len(profiles) + 1)])
        selected = profiles[int(choice) - 1]
        
        if Confirm.ask(f"Delete profile '{selected}'?", default=False):
            await self.manager.delete_profile(selected)
            console.print(f"[green]Profile '{selected}' deleted.[/green]")
    
    async def _export_profile(self) -> None:
        """Export a profile to .env."""
        profiles = await self.manager.list_profiles()
        if not profiles:
            console.print("[yellow]No profiles available.[/yellow]")
            return
        
        console.print("\nSelect profile to export:")
        for i, name in enumerate(profiles, 1):
            console.print(f"  {i}. {name}")
        
        choice = Prompt.ask("Select profile", choices=[str(i) for i in range(1, len(profiles) + 1)])
        selected = profiles[int(choice) - 1]
        
        env_path = Prompt.ask("Export to file", default=".env")
        
        if Path(env_path).exists():
            if not Confirm.ask(f"File '{env_path}' exists. Overwrite?"):
                return
        
        await self.manager.export_to_env(selected, env_path)
        console.print(f"[green]Profile exported to '{env_path}'[/green]")


if __name__ == "__main__":
    import asyncio
    
    async def main():
        wizard = ProfileWizard()
        await wizard.run()
    
    asyncio.run(main())