#!/usr/bin/env python3
"""
Test the profile management system.
"""

import asyncio
from rich.console import Console
from src.utils.profile_manager import ProfileManager, ProfileWizard

console = Console()


async def test_profile_manager():
    """Test basic profile manager operations."""
    console.print("[bold cyan]Testing Profile Manager[/bold cyan]\n")
    
    manager = ProfileManager("./test_profiles")
    
    # Create test profiles
    console.print("Creating test profiles...")
    
    await manager.create_profile("homelab", {
        "PROXMOX_HOST": "192.168.10.200",
        "PROXMOX_USER": "root@pam",
        "PROXMOX_PASSWORD": "homelab123",
        "PROXMOX_VERIFY_SSL": "false"
    })
    
    await manager.create_profile("dev-cluster", {
        "PROXMOX_HOST": "10.0.0.50",
        "PROXMOX_USER": "admin@pve",
        "PROXMOX_PASSWORD": "devpass456",
        "PROXMOX_VERIFY_SSL": "true"
    })
    
    await manager.create_profile("cloud-vps", {
        "PROXMOX_HOST": "proxmox.example.com",
        "PROXMOX_USER": "root@pam",
        "PROXMOX_PASSWORD": "cloudpass789",
        "PROXMOX_VERIFY_SSL": "true"
    })
    
    # List profiles
    console.print("\n[bold]All Profiles:[/bold]")
    profiles = await manager.load_profiles()
    manager.display_profiles(profiles)
    
    # Set active profile
    console.print("\nSetting 'homelab' as active profile...")
    await manager.set_active_profile("homelab")
    
    active = await manager.get_active_profile()
    console.print(f"Active profile: [green]{active}[/green]")
    
    # Show profiles with active indicator
    console.print("\n[bold]Profiles (with active indicator):[/bold]")
    manager.display_profiles(profiles, active)
    
    # Export to test env
    console.print("\nExporting active profile to test.env...")
    await manager.export_to_env("homelab", "test.env")
    console.print("[green]Exported successfully![/green]")
    
    # Clean up
    import shutil
    shutil.rmtree("./test_profiles", ignore_errors=True)
    import os
    if os.path.exists("test.env"):
        os.remove("test.env")


async def test_profile_wizard():
    """Test the interactive profile wizard."""
    console.print("\n[bold cyan]Testing Profile Wizard[/bold cyan]")
    console.print("[dim]This would normally be interactive. Showing structure only.[/dim]\n")
    
    wizard = ProfileWizard()
    wizard.manager.profile_dir = "./test_profiles_wizard"
    
    # Show what the wizard would do
    console.print("Profile Wizard Menu:")
    console.print("1. List profiles")
    console.print("2. Create new profile")
    console.print("3. Switch active profile")
    console.print("4. Edit profile")
    console.print("5. Delete profile")
    console.print("6. Export profile to .env")
    console.print("7. Exit")
    
    # Clean up
    import shutil
    shutil.rmtree("./test_profiles_wizard", ignore_errors=True)


async def demonstrate_multi_server_workflow():
    """Demonstrate how to work with multiple Proxmox servers."""
    console.print("\n[bold cyan]Multi-Server Workflow Demonstration[/bold cyan]\n")
    
    manager = ProfileManager("./demo_profiles")
    
    # Scenario: User has 3 different Proxmox servers
    console.print("[yellow]Scenario:[/yellow] You manage 3 different Proxmox environments\n")
    
    # Create profiles for each
    environments = [
        ("production", "192.168.1.10", "Production Proxmox Cluster"),
        ("staging", "192.168.2.10", "Staging Environment"),
        ("homelab", "192.168.10.200", "Home Lab Server")
    ]
    
    for name, host, desc in environments:
        console.print(f"Creating profile '{name}' for {desc}...")
        await manager.create_profile(name, {
            "PROXMOX_HOST": host,
            "PROXMOX_USER": "root@pam",
            "PROXMOX_PASSWORD": f"{name}_pass",
            "PROXMOX_VERIFY_SSL": "false",
            "TEMPLATE_VM_ID": "9000" if name == "production" else "9001",
            "TEMPLATE_VM_NAME": f"{name}-ubuntu-template"
        })
    
    console.print("\n[bold]Workflow Examples:[/bold]\n")
    
    # Example 1: Switch between environments
    console.print("1. [cyan]Switching to production:[/cyan]")
    await manager.set_active_profile("production")
    await manager.export_to_env("production", ".env.demo")
    console.print("   → Now connected to production server at 192.168.1.10")
    
    console.print("\n2. [cyan]Quick switch to homelab:[/cyan]")
    await manager.set_active_profile("homelab")
    await manager.export_to_env("homelab", ".env.demo")
    console.print("   → Now connected to homelab server at 192.168.10.200")
    
    # Example 2: Show how templates differ
    console.print("\n3. [cyan]Different templates per environment:[/cyan]")
    for name, _, _ in environments:
        profile = await manager.get_profile(name)
        console.print(f"   • {name}: Template ID {profile['TEMPLATE_VM_ID']} - {profile['TEMPLATE_VM_NAME']}")
    
    # Clean up
    import shutil
    shutil.rmtree("./demo_profiles", ignore_errors=True)
    import os
    if os.path.exists(".env.demo"):
        os.remove(".env.demo")


async def main():
    """Run all tests."""
    tests = [
        ("Profile Manager Basic Operations", test_profile_manager),
        ("Profile Wizard Structure", test_profile_wizard),
        ("Multi-Server Workflow", demonstrate_multi_server_workflow)
    ]
    
    for name, test_func in tests:
        console.print(f"\n{'='*60}")
        console.print(f"[bold]{name}[/bold]")
        console.print(f"{'='*60}\n")
        
        try:
            await test_func()
        except Exception as e:
            console.print(f"[red]Test failed: {e}[/red]")
            import traceback
            traceback.print_exc()
        
        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()


if __name__ == "__main__":
    asyncio.run(main())