#!/usr/bin/env python3
"""
Test script for Proxmox API token creation.
"""

import asyncio
import sys
import pytest
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.proxmox_api import ProxmoxAPIClient
from rich.console import Console

console = Console()


@pytest.mark.requires_proxmox
async def test_token_creation():
    """Test creating an API token."""
    # Test credentials - you'll need to update these
    host = "192.168.10.200"
    username = "root@pam"
    password = "Tenchi01!"  # Update with your password
    
    console.print("[bold]Testing Proxmox API Token Creation[/bold]\n")
    
    # Initialize client with password auth
    client = ProxmoxAPIClient(
        host=host,
        username=username,
        password=password,
        verify_ssl=False
    )
    
    # Authenticate
    console.print("1. Authenticating with password...")
    if not await client.authenticate():
        console.print("[red]Authentication failed![/red]")
        return
    console.print("[green]✓ Authenticated[/green]")
    
    # List existing tokens
    console.print("\n2. Listing existing tokens...")
    tokens = await client.list_api_tokens(username)
    console.print(f"Found {len(tokens)} existing tokens:")
    for token in tokens:
        console.print(f"  - {token.get('tokenid')} ({token.get('comment', 'No comment')})")
    
    # Create a test token
    token_id = "test-token"
    console.print(f"\n3. Creating token '{token_id}'...")
    
    try:
        result = await client.create_api_token(
            userid=username,
            tokenid=token_id,
            comment="Test token created by script",
            expire=0,
            privsep=False
        )
        
        console.print("[green]✓ Token created successfully![/green]")
        console.print(f"Full token: {result['full-tokenid']}={result['value']}")
        
        # Test the token
        console.print("\n4. Testing the new token...")
        token_client = ProxmoxAPIClient(
            host=host,
            api_token=f"{result['full-tokenid']}={result['value']}",
            verify_ssl=False
        )
        
        if await token_client.authenticate():
            nodes = await token_client.list_nodes()
            console.print(f"[green]✓ Token works! Found {len(nodes)} nodes[/green]")
        else:
            console.print("[red]Token test failed[/red]")
        
        # Clean up - delete test token
        console.print(f"\n5. Cleaning up - deleting test token...")
        if await client.delete_api_token(username, token_id):
            console.print("[green]✓ Test token deleted[/green]")
        else:
            console.print("[yellow]Failed to delete test token[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    asyncio.run(test_token_creation())