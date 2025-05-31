#!/usr/bin/env python3
"""
Test secure credential storage with current credentials.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.credential_manager import get_credential_manager
from src.utils.secure_config import get_secure_config, get_proxmox_client_config
from src.utils.proxmox_api import ProxmoxAPIClient
from config import Config
from rich.console import Console
from rich.table import Table

console = Console()


async def test_credential_storage():
    """Test storing and retrieving credentials securely."""
    console.print("[bold]Testing Secure Credential Storage[/bold]\n")
    
    cm = get_credential_manager()
    
    # 1. Store current credentials
    console.print("1. Storing current credentials in secure storage...")
    
    # Store Proxmox credentials
    if Config.PROXMOX_PASSWORD:
        await cm.set_credential("proxmox", "password", Config.PROXMOX_PASSWORD)
        console.print("   [green]✓[/green] Stored Proxmox password")
    
    if Config.PROXMOX_API_TOKEN:
        await cm.set_credential("proxmox", "api_token", Config.PROXMOX_API_TOKEN)
        console.print("   [green]✓[/green] Stored Proxmox API token")
    
    # 2. Retrieve and verify
    console.print("\n2. Retrieving credentials from secure storage...")
    
    password = await cm.get_credential("proxmox", "password")
    token = await cm.get_credential("proxmox", "api_token")
    
    # Display results (masked)
    table = Table(title="Retrieved Credentials")
    table.add_column("Credential", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Value (masked)")
    
    table.add_row(
        "Proxmox Password",
        "✓ Found" if password else "✗ Not found",
        f"{'*' * 8}..." if password else "N/A"
    )
    
    table.add_row(
        "Proxmox API Token", 
        "✓ Found" if token else "✗ Not found",
        f"{token[:20]}...{token[-10:]}" if token else "N/A"
    )
    
    console.print(table)
    
    # 3. Test secure config integration
    console.print("\n3. Testing SecureConfig integration...")
    
    secure_config = get_secure_config()
    await secure_config.initialize()
    
    # Get complete Proxmox config
    proxmox_config = await get_proxmox_client_config()
    
    console.print("   Proxmox configuration loaded:")
    console.print(f"   - Host: {proxmox_config.get('host')}")
    console.print(f"   - Has API Token: {'Yes' if proxmox_config.get('api_token') else 'No'}")
    console.print(f"   - Has Password: {'Yes' if proxmox_config.get('password') else 'No'}")
    
    # 4. Test with actual Proxmox connection
    console.print("\n4. Testing Proxmox connection with secure credentials...")
    
    try:
        # Create client with secure config
        if proxmox_config.get("api_token"):
            client = ProxmoxAPIClient(
                host=proxmox_config["host"],
                api_token=proxmox_config["api_token"],
                verify_ssl=proxmox_config.get("verify_ssl", False)
            )
        else:
            client = ProxmoxAPIClient(
                host=proxmox_config["host"],
                username=proxmox_config.get("username"),
                password=proxmox_config.get("password"),
                verify_ssl=proxmox_config.get("verify_ssl", False)
            )
        
        # Test authentication
        if await client.authenticate():
            console.print("   [green]✓[/green] Authentication successful!")
            
            # Try to list nodes
            nodes = await client.list_nodes()
            console.print(f"   [green]✓[/green] Retrieved {len(nodes)} node(s)")
            
            for node in nodes:
                console.print(f"      - {node.node} ({node.status})")
        else:
            console.print("   [red]✗[/red] Authentication failed")
            
    except Exception as e:
        console.print(f"   [red]✗[/red] Connection error: {e}")
    
    # 5. Check storage location
    console.print("\n5. Storage information:")
    
    from src.utils.credential_manager import EncryptedFileBackend
    backend = EncryptedFileBackend()
    console.print(f"   - Storage location: {backend.storage_path}")
    console.print(f"   - File exists: {backend.storage_path.exists()}")
    if backend.storage_path.exists():
        size = backend.storage_path.stat().st_size
        console.print(f"   - File size: {size} bytes")
    
    # 6. List all stored credentials
    console.print("\n6. All stored credential keys:")
    all_keys = await cm.backend.list_keys()
    for key in sorted(all_keys):
        console.print(f"   - {key}")


async def test_migration():
    """Test migrating from .env to secure storage."""
    console.print("\n[bold]Testing Credential Migration[/bold]\n")
    
    cm = get_credential_manager()
    
    # Check what would be migrated
    console.print("Credentials that would be migrated:")
    
    migrations = [
        ("proxmox", "password", Config.PROXMOX_PASSWORD, "PROXMOX_PASSWORD"),
        ("proxmox", "api_token", Config.PROXMOX_API_TOKEN, "PROXMOX_API_TOKEN"),
    ]
    
    table = Table(title="Migration Preview")
    table.add_column("Service", style="cyan")
    table.add_column("Key", style="yellow")
    table.add_column("Source", style="magenta")
    table.add_column("Has Value", style="green")
    
    for service, key, value, env_name in migrations:
        table.add_row(
            service,
            key,
            env_name,
            "Yes" if value and value != "" else "No"
        )
    
    console.print(table)
    
    # Note about actual migration
    console.print("\n[yellow]Note:[/yellow] To actually migrate credentials, run with:")
    console.print("  export MCP_MIGRATE_CREDENTIALS=true")
    console.print("  python tests/test_secure_storage.py")


async def main():
    """Run all tests."""
    try:
        await test_credential_storage()
        await test_migration()
        
        console.print("\n[bold green]✓ All tests completed![/bold green]")
        
    except Exception as e:
        console.print(f"\n[bold red]✗ Test failed: {e}[/bold red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())