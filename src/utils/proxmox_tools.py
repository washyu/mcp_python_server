"""
Proxmox tools and utilities for MCP server.
Includes connection testing, API helpers, and Proxmox operations.
"""

import asyncio
import aiohttp
import ssl
from typing import Dict, Any, Tuple, Optional
from rich.console import Console
from rich.prompt import Confirm
from src.utils.proxmox_api import ProxmoxAPIClient

console = Console()


class ProxmoxConnectionTest:
    """Test connection to Proxmox server."""
    
    @staticmethod
    async def test_connection(
        host: str, 
        username: str, 
        password: str, 
        verify_ssl: bool = False
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Test connection to Proxmox server.
        
        Returns:
            Tuple of (success, cluster_info, error_message)
        """
        # Ensure host has protocol
        if not host.startswith(('http://', 'https://')):
            host = f"https://{host}"
        
        # Remove trailing slash
        host = host.rstrip('/')
        
        # Proxmox API endpoint
        auth_url = f"{host}:8006/api2/json/access/ticket"
        version_url = f"{host}:8006/api2/json/version"
        
        # SSL context
        ssl_context = None
        if not verify_ssl:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                # Step 1: Authenticate
                auth_data = {
                    'username': username,
                    'password': password
                }
                
                async with session.post(auth_url, data=auth_data) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return False, None, f"Authentication failed: {error_text}"
                    
                    auth_response = await resp.json()
                    ticket = auth_response['data']['ticket']
                    csrf_token = auth_response['data']['CSRFPreventionToken']
                
                # Step 2: Get version info with auth
                headers = {
                    'Cookie': f"PVEAuthCookie={ticket}",
                    'CSRFPreventionToken': csrf_token
                }
                
                async with session.get(version_url, headers=headers) as resp:
                    if resp.status != 200:
                        return False, None, f"Failed to get version info: {resp.status}"
                    
                    version_data = await resp.json()
                    
                    return True, {
                        'version': version_data['data']['version'],
                        'release': version_data['data']['release'],
                        'repoid': version_data['data']['repoid']
                    }, None
                    
        except aiohttp.ClientConnectorError as e:
            return False, None, f"Connection failed: Cannot reach {host}:8006 - {str(e)}"
        except Exception as e:
            return False, None, f"Unexpected error: {str(e)}"
    
    @staticmethod
    async def test_and_display(
        host: str, 
        username: str, 
        password: str, 
        verify_ssl: str = "false",
        offer_token_creation: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Test connection and display results, optionally create API token.
        
        Returns:
            Tuple of (success, api_token_if_created)
        """
        console.print("\n[yellow]Testing Proxmox connection...[/yellow]")
        
        # Convert verify_ssl string to bool
        verify_ssl_bool = verify_ssl.lower() in ['true', 'yes', '1']
        
        with console.status("[bold cyan]Connecting to Proxmox...[/bold cyan]", spinner="dots"):
            success, info, error = await ProxmoxConnectionTest.test_connection(
                host, username, password, verify_ssl_bool
            )
        
        if success:
            console.print("[green]✓ Connection successful![/green]")
            if info:
                console.print(f"  Proxmox VE {info['version']}")
                console.print(f"  Release: {info['release']}")
            
            # Offer to create API token during connection test
            if offer_token_creation and password:  # Only if using password auth
                console.print("\n[cyan]For better reliability, MCP can create an API token.[/cyan]")
                console.print("[dim]API tokens don't expire and work better for automation.[/dim]")
                
                if Confirm.ask("\nCreate API token now?", default=True):
                    token = await ProxmoxConnectionTest.create_mcp_token(
                        host, username, password, verify_ssl
                    )
                    return True, token
            
            return True, None
        else:
            console.print(f"[red]✗ Connection failed![/red]")
            console.print(f"  Error: {error}")
            return False, None
    
    @staticmethod
    async def create_mcp_token(
        host: str,
        username: str,
        password: str,
        verify_ssl: str = "false",
        token_id: str = "mcp-server"
    ) -> Optional[str]:
        """
        Create an API token for MCP server use.
        
        Args:
            host: Proxmox host
            username: Username (must have permissions to create tokens)
            password: Password
            verify_ssl: Whether to verify SSL
            token_id: ID for the token (default: mcp-server)
            
        Returns:
            Full token string (user@realm!tokenid=value) or None if failed
        """
        console.print("\n[yellow]Creating API token for MCP server...[/yellow]")
        
        # Initialize client with password auth
        client = ProxmoxAPIClient(
            host=host,
            username=username,
            password=password,
            verify_ssl=verify_ssl.lower() in ['true', 'yes', '1']
        )
        
        try:
            # Authenticate first
            if not await client.authenticate():
                console.print("[red]Failed to authenticate[/red]")
                return None
            
            # Check existing tokens
            console.print(f"[dim]Checking for existing '{token_id}' token...[/dim]")
            existing_tokens = await client.list_api_tokens(username)
            
            # Check if token already exists
            token_exists = any(t.get('tokenid') == token_id for t in existing_tokens)
            
            if token_exists:
                console.print(f"[yellow]Token '{token_id}' already exists.[/yellow]")
                
                if Confirm.ask("Delete existing token and create new one?", default=True):
                    # Delete existing token
                    if await client.delete_api_token(username, token_id):
                        console.print(f"[green]✓ Deleted existing token[/green]")
                    else:
                        console.print(f"[red]Failed to delete existing token[/red]")
                        return None
                else:
                    console.print("[yellow]Keeping existing token[/yellow]")
                    return None
            
            # Create new token
            console.print(f"[dim]Creating new API token '{token_id}'...[/dim]")
            
            token_result = await client.create_api_token(
                userid=username,
                tokenid=token_id,
                comment="MCP Server API Token - Auto-generated",
                expire=0,  # Never expire
                privsep=False  # Use full user permissions
            )
            
            if token_result and token_result.get('value'):
                full_token = f"{token_result['full-tokenid']}={token_result['value']}"
                console.print(f"\n[green]✓ API Token created successfully![/green]")
                console.print(f"\n[bold]Token:[/bold] {full_token}")
                console.print("\n[yellow]⚠️  Save this token! It won't be shown again.[/yellow]")
                
                # Offer to test the token
                if Confirm.ask("\nTest the new token?", default=True):
                    test_client = ProxmoxAPIClient(
                        host=host,
                        api_token=full_token,
                        verify_ssl=verify_ssl.lower() in ['true', 'yes', '1']
                    )
                    
                    if await test_client.authenticate():
                        nodes = await test_client.list_nodes()
                        console.print(f"[green]✓ Token works! Found {len(nodes)} node(s)[/green]")
                    else:
                        console.print("[red]✗ Token test failed[/red]")
                
                return full_token
            else:
                console.print("[red]Failed to create token[/red]")
                return None
                
        except Exception as e:
            console.print(f"[red]Error creating token: {e}[/red]")
            return None


if __name__ == "__main__":
    # Test the connection
    async def test():
        import sys
        if len(sys.argv) < 4:
            print("Usage: python proxmox_test.py <host> <username> <password>")
            sys.exit(1)
        
        host = sys.argv[1]
        username = sys.argv[2]
        password = sys.argv[3]
        
        await ProxmoxConnectionTest.test_and_display(host, username, password)
    
    asyncio.run(test())