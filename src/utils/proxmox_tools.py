"""
Proxmox tools and utilities for MCP server.
Includes connection testing, API helpers, and Proxmox operations.
"""

import asyncio
import aiohttp
import ssl
from typing import Dict, Any, Tuple, Optional
from rich.console import Console

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
        verify_ssl: str = "false"
    ) -> bool:
        """Test connection and display results."""
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
            return True
        else:
            console.print(f"[red]✗ Connection failed![/red]")
            console.print(f"  Error: {error}")
            return False


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