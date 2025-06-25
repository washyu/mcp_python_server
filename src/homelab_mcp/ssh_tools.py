"""SSH-based tools for system discovery and management."""

import asyncio
import json
import os
import getpass
from pathlib import Path
from typing import Dict, Any, Optional, cast
import asyncssh


def get_mcp_ssh_key_path() -> Path:
    """Get the path to the MCP SSH key."""
    home_dir = Path.home()
    ssh_dir = home_dir / '.ssh'
    return ssh_dir / 'mcp_admin_rsa'


def get_mcp_public_key_path() -> Path:
    """Get the path to the MCP SSH public key."""
    return get_mcp_ssh_key_path().with_suffix('.pub')


async def ensure_mcp_ssh_key() -> str:
    """Ensure MCP has its own SSH key, generate if missing."""
    key_path = get_mcp_ssh_key_path()
    pub_key_path = get_mcp_public_key_path()
    
    # Check if key already exists
    if key_path.exists() and pub_key_path.exists():
        return str(key_path)
    
    # Create .ssh directory if it doesn't exist
    ssh_dir = key_path.parent
    ssh_dir.mkdir(mode=0o700, exist_ok=True)
    
    # Generate SSH key pair
    private_key = asyncssh.generate_private_key('ssh-rsa', key_size=2048)
    public_key = private_key.export_public_key()
    
    # Write private key
    with open(key_path, 'wb') as f:
        f.write(private_key.export_private_key())
    key_path.chmod(0o600)
    
    # Write public key with mcp_admin comment
    with open(pub_key_path, 'w') as f:
        f.write(f"{public_key.decode()} mcp_admin@{os.uname().nodename}\n")
    pub_key_path.chmod(0o644)
    
    return str(key_path)


async def setup_remote_mcp_admin(
    hostname: str,
    username: str, 
    password: str,
    force_update_key: bool = True,
    port: int = 22
) -> str:
    """SSH into remote system and setup mcp_admin user with admin permissions."""
    try:
        # Ensure we have our SSH key
        key_path = await ensure_mcp_ssh_key()
        pub_key_path = get_mcp_public_key_path()
        
        if not pub_key_path.exists():
            raise ValueError("MCP public key not found")
        
        # Read our public key
        with open(pub_key_path, 'r') as f:
            public_key = f.read().strip()
        
        # Connect to remote system
        connect_kwargs = {
            "host": hostname,
            "port": port,
            "username": username,
            "password": password,
            "known_hosts": None,
            "connect_timeout": 10
        }
        
        async with await asyncssh.connect(**connect_kwargs) as conn:
            setup_results = {}
            
            # Check if mcp_admin user already exists
            user_check = await conn.run('id mcp_admin', check=False)
            user_exists = user_check.exit_status == 0
            
            if not user_exists:
                # Clean up any leftover home directory before creating user
                await conn.run('sudo rm -rf /home/mcp_admin', check=False)
                
                # Create mcp_admin user
                create_user = await conn.run(
                    'sudo useradd -m -s /bin/bash -G sudo mcp_admin', 
                    check=False
                )
                if create_user.exit_status != 0:
                    setup_results['user_creation'] = f"Failed: {create_user.stderr}"
                else:
                    setup_results['user_creation'] = "Success: mcp_admin user created"
                    # Ensure proper ownership of home directory
                    await conn.run('sudo chown -R mcp_admin:mcp_admin /home/mcp_admin', check=False)
            else:
                setup_results['user_creation'] = "User already exists"
            
            # Ensure mcp_admin is in sudo group
            sudo_group = await conn.run('sudo usermod -a -G sudo mcp_admin', check=False)
            if sudo_group.exit_status == 0:
                setup_results['sudo_access'] = "Success: Added to sudo group"
            else:
                setup_results['sudo_access'] = f"Failed: {sudo_group.stderr}"
            
            # Check if our key is already in authorized_keys
            key_check = await conn.run(
                f'sudo grep -F "{public_key}" /home/mcp_admin/.ssh/authorized_keys 2>/dev/null',
                check=False
            )
            
            key_exists = key_check.exit_status == 0
            
            if key_exists and not force_update_key:
                setup_results['ssh_key'] = "SSH key already exists"
            else:
                # Setup SSH directory (more robust approach)
                # First ensure the home directory exists and has proper ownership
                await conn.run('sudo mkdir -p /home/mcp_admin', check=False)
                await conn.run('sudo chown mcp_admin:mcp_admin /home/mcp_admin', check=False)
                
                # Create .ssh directory as root, then change ownership
                mkdir_cmd = await conn.run(
                    'sudo mkdir -p /home/mcp_admin/.ssh && '
                    'sudo chown mcp_admin:mcp_admin /home/mcp_admin/.ssh && '
                    'sudo chmod 700 /home/mcp_admin/.ssh',
                    check=False
                )
                
                if mkdir_cmd.exit_status != 0:
                    setup_results['ssh_key'] = f"Failed to create .ssh directory: {mkdir_cmd.stderr}"
                else:
                    if force_update_key and key_exists:
                        # Remove old MCP keys (those with mcp_admin@ comment)
                        await conn.run(
                            'sudo grep -v "mcp_admin@" /home/mcp_admin/.ssh/authorized_keys | '
                            'sudo -u mcp_admin tee /home/mcp_admin/.ssh/authorized_keys.tmp && '
                            'sudo -u mcp_admin mv /home/mcp_admin/.ssh/authorized_keys.tmp /home/mcp_admin/.ssh/authorized_keys',
                            check=False
                        )
                        
                    # Add new key
                    add_key = await conn.run(
                        f'echo "{public_key}" | sudo -u mcp_admin tee -a /home/mcp_admin/.ssh/authorized_keys && '
                        'sudo -u mcp_admin chmod 600 /home/mcp_admin/.ssh/authorized_keys',
                        check=False
                    )
                    
                    if add_key.exit_status == 0:
                        if key_exists and force_update_key:
                            setup_results['ssh_key'] = "Success: SSH key updated"
                        else:
                            setup_results['ssh_key'] = "Success: SSH key installed"
                    else:
                        setup_results['ssh_key'] = f"Failed: {add_key.stderr}"
            
            # Enable passwordless sudo for mcp_admin
            sudoers_setup = await conn.run(
                'echo "mcp_admin ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/mcp_admin',
                check=False
            )
            
            if sudoers_setup.exit_status == 0:
                setup_results['passwordless_sudo'] = "Success: Passwordless sudo enabled"
            else:
                setup_results['passwordless_sudo'] = f"Failed: {sudoers_setup.stderr}"
            
            # Test SSH key authentication
            test_conn = await conn.run('sudo -u mcp_admin whoami', check=False)
            if test_conn.exit_status == 0:
                setup_results['test_access'] = "Success: mcp_admin access verified"
            else:
                setup_results['test_access'] = f"Failed: {test_conn.stderr}"
        
        return json.dumps({
            "status": "success",
            "hostname": hostname,
            "mcp_admin_setup": setup_results,
            "ssh_key_path": key_path,
            "public_key": public_key
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "hostname": hostname,
            "error": str(e)
        }, indent=2)


async def verify_mcp_admin_access(hostname: str, port: int = 22) -> str:
    """Verify SSH key access to mcp_admin account on remote system."""
    try:
        key_path = get_mcp_ssh_key_path()
        
        if not key_path.exists():
            return json.dumps({
                "status": "error",
                "hostname": hostname,
                "error": "MCP SSH key not found. Run ensure_mcp_ssh_key() first."
            }, indent=2)
        
        # Test SSH connection with key
        connect_kwargs = {
            "host": hostname,
            "port": port,
            "username": "mcp_admin",
            "client_keys": [str(key_path)],
            "known_hosts": None,
            "connect_timeout": 10
        }
        
        async with await asyncssh.connect(**connect_kwargs) as conn:
            # Test basic access
            whoami_result = await conn.run('whoami', check=False)
            if whoami_result.exit_status != 0:
                raise Exception("Failed to execute whoami command")
            
            # Test sudo access
            sudo_result = await conn.run('sudo -n whoami', check=False)
            sudo_access = sudo_result.exit_status == 0
            
            # Get system hostname
            hostname_result = await conn.run('hostname', check=False)
            remote_hostname = hostname
            if hostname_result.exit_status == 0 and hostname_result.stdout:
                remote_hostname = cast(str, hostname_result.stdout).strip()
            
            return json.dumps({
                "status": "success",
                "hostname": remote_hostname,
                "connection_ip": hostname,
                "mcp_admin": {
                    "ssh_access": "Success: Connected with SSH key",
                    "sudo_access": "Success: Passwordless sudo working" if sudo_access else "Failed: No sudo access",
                    "username": cast(str, whoami_result.stdout).strip() if whoami_result.stdout else "unknown"
                }
            }, indent=2)
        
    except asyncssh.misc.PermissionDenied:
        return json.dumps({
            "status": "error",
            "hostname": hostname,
            "error": "SSH key authentication failed for mcp_admin"
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "hostname": hostname,
            "error": str(e)
        }, indent=2)


async def ssh_discover_system(
    hostname: str, 
    username: str, 
    password: Optional[str] = None, 
    key_path: Optional[str] = None,
    port: int = 22
) -> str:
    """SSH into a system and gather hardware/system information."""
    try:
        # Connect via SSH
        connect_kwargs = {
            "host": hostname,
            "port": port,
            "username": username,
            "known_hosts": None,
            "connect_timeout": 10
        }
        
        if key_path:
            connect_kwargs["client_keys"] = [key_path]
        elif password:
            connect_kwargs["password"] = password
        elif username == "mcp_admin":
            # Use MCP key for mcp_admin user if available
            mcp_key_path = get_mcp_ssh_key_path()
            if mcp_key_path.exists():
                connect_kwargs["client_keys"] = [str(mcp_key_path)]
            else:
                raise ValueError("MCP SSH key not found and no password provided for mcp_admin")
        else:
            raise ValueError("Either password or key_path must be provided")
        
        async with await asyncssh.connect(**connect_kwargs) as conn:
            system_info = {}
            
            # Get actual hostname from the remote system
            hostname_result = await conn.run('hostname', check=False)
            actual_hostname = hostname
            if hostname_result.exit_status == 0 and hostname_result.stdout:
                actual_hostname = cast(str, hostname_result.stdout).strip()
            
            # Get CPU information (supports both x86 and ARM/Pi systems)
            cpu_cores_result = await conn.run('nproc', check=False)
            cpu_cores = None
            if cpu_cores_result.exit_status == 0 and cpu_cores_result.stdout:
                cpu_cores = cast(str, cpu_cores_result.stdout).strip()
            
            # Try different methods to get CPU model
            cpu_model = None
            
            # Method 1: Try x86 "model name"
            cpu_model_result = await conn.run('cat /proc/cpuinfo | grep "model name" | head -1', check=False)
            if cpu_model_result.exit_status == 0 and cpu_model_result.stdout and cpu_model_result.stdout.strip():
                model_line = cast(str, cpu_model_result.stdout).strip()
                if ':' in model_line:
                    cpu_model = model_line.split(':', 1)[1].strip()
            
            # Method 2: Try ARM/Pi "Model" field
            if not cpu_model:
                pi_model_result = await conn.run('cat /proc/cpuinfo | grep -E "^Model" | head -1', check=False)
                if pi_model_result.exit_status == 0 and pi_model_result.stdout and pi_model_result.stdout.strip():
                    model_line = cast(str, pi_model_result.stdout).strip()
                    if ':' in model_line:
                        cpu_model = model_line.split(':', 1)[1].strip()
            
            # Method 3: Try lscpu for CPU name (works on both x86 and ARM)
            if not cpu_model:
                lscpu_result = await conn.run('lscpu | grep "Model name" | head -1', check=False)
                if lscpu_result.exit_status == 0 and lscpu_result.stdout and lscpu_result.stdout.strip():
                    model_line = cast(str, lscpu_result.stdout).strip()
                    if ':' in model_line:
                        cpu_model = model_line.split(':', 1)[1].strip()
            
            # Method 4: Fallback to Hardware field for older ARM systems
            if not cpu_model:
                hw_result = await conn.run('cat /proc/cpuinfo | grep "Hardware" | head -1', check=False)
                if hw_result.exit_status == 0 and hw_result.stdout and hw_result.stdout.strip():
                    hw_line = cast(str, hw_result.stdout).strip()
                    if ':' in hw_line:
                        cpu_model = hw_line.split(':', 1)[1].strip()
            
            # Store CPU info if we got anything
            if cpu_model or cpu_cores:
                system_info['cpu'] = {}
                if cpu_model:
                    system_info['cpu']['model'] = cpu_model
                if cpu_cores:
                    system_info['cpu']['cores'] = cpu_cores
            
            # Get memory information
            mem_result = await conn.run('free -h', check=False)
            if mem_result.exit_status == 0 and mem_result.stdout:
                mem_lines = cast(str, mem_result.stdout).strip().split('\n')
                if len(mem_lines) > 1:
                    # Parse the memory line (second line after header)
                    mem_data = mem_lines[1].split()
                    if len(mem_data) >= 7:
                        system_info['memory'] = {
                            'total': mem_data[1],
                            'used': mem_data[2],
                            'free': mem_data[3],
                            'available': mem_data[6]
                        }
            
            # Get disk information  
            disk_result = await conn.run('df -h /', check=False)
            if disk_result.exit_status == 0 and disk_result.stdout:
                disk_lines = cast(str, disk_result.stdout).strip().split('\n')
                if len(disk_lines) > 1:
                    # Parse the disk line (second line after header)
                    disk_data = disk_lines[1].split()
                    if len(disk_data) >= 6:
                        system_info['disk'] = {
                            'filesystem': disk_data[0],
                            'size': disk_data[1],
                            'used': disk_data[2],
                            'available': disk_data[3],
                            'use_percent': disk_data[4],
                            'mount': disk_data[5]
                        }
            
            # Get network interfaces
            net_result = await conn.run('ip -j addr show', check=False)
            if net_result.exit_status == 0 and net_result.stdout:
                try:
                    interfaces = json.loads(cast(str, net_result.stdout))
                    network_info = []
                    for iface in interfaces:
                        if iface.get('ifname') != 'lo':  # Skip loopback
                            iface_info = {
                                'name': iface.get('ifname'),
                                'state': iface.get('operstate'),
                                'addresses': []
                            }
                            for addr_info in iface.get('addr_info', []):
                                if addr_info.get('family') == 'inet':
                                    iface_info['addresses'].append(addr_info.get('local'))
                            if iface_info['addresses']:
                                network_info.append(iface_info)
                    system_info['network'] = network_info
                except json.JSONDecodeError:
                    # Fallback to basic parsing if JSON output not supported
                    pass
            
            # Get system uptime
            uptime_result = await conn.run('uptime -p', check=False)
            if uptime_result.exit_status == 0 and uptime_result.stdout:
                system_info['uptime'] = cast(str, uptime_result.stdout).strip()
            
            # Get OS information
            os_result = await conn.run('cat /etc/os-release | grep PRETTY_NAME', check=False)
            if os_result.exit_status == 0 and os_result.stdout:
                os_line = cast(str, os_result.stdout).strip()
                if '=' in os_line:
                    system_info['os'] = os_line.split('=', 1)[1].strip('"')
        
        return json.dumps({
            "status": "success",
            "hostname": actual_hostname,
            "connection_ip": hostname,
            "data": system_info
        }, indent=2)
        
    except asyncssh.misc.PermissionDenied:
        return json.dumps({
            "status": "error",
            "connection_ip": hostname,
            "error": "SSH authentication failed"
        }, indent=2)
    except asyncssh.misc.ConnectionLost:
        return json.dumps({
            "status": "error", 
            "connection_ip": hostname,
            "error": "SSH connection lost"
        }, indent=2)
    except asyncio.TimeoutError:
        return json.dumps({
            "status": "error",
            "connection_ip": hostname,
            "error": "SSH connection timeout"
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "connection_ip": hostname,
            "error": str(e)
        }, indent=2)


async def ssh_execute_command(
    hostname: str,
    username: str,
    command: str,
    password: Optional[str] = None,
    sudo: bool = False,
    port: int = 22,
    **kwargs
) -> str:
    """Execute a command on a remote system via SSH."""
    ssh_key_path = None
    client_keys = []
    
    # Use MCP admin key if username is mcp_admin
    if username == 'mcp_admin':
        mcp_key_path = await ensure_mcp_ssh_key()
        if mcp_key_path:
            client_keys = [mcp_key_path]
    
    # Prepare connection options
    connect_kwargs = {
        'host': hostname,
        'port': port,
        'username': username,
        'known_hosts': None
    }
    
    if client_keys:
        connect_kwargs['client_keys'] = client_keys
    
    if password:
        connect_kwargs['password'] = password
    
    try:
        async with asyncssh.connect(**connect_kwargs) as conn:
            # Prepare the command with sudo if requested
            if sudo:
                if username == 'mcp_admin':
                    # mcp_admin has passwordless sudo
                    full_command = f"sudo {command}"
                else:
                    # Other users might need password for sudo
                    full_command = f"echo '{password}' | sudo -S {command}" if password else f"sudo {command}"
            else:
                full_command = command
            
            # Execute the command
            result = await conn.run(full_command, check=False)
            
            output = []
            if result.stdout:
                output.append(f"Output:\n{result.stdout.strip()}")
            if result.stderr:
                output.append(f"Error:\n{result.stderr.strip()}")
            
            return json.dumps({
                "status": "success",
                "hostname": hostname,
                "command": command,
                "exit_code": result.exit_status,
                "output": "\n\n".join(output) if output else "Command executed successfully (no output)"
            }, indent=2)
            
    except asyncssh.misc.PermissionDenied:
        return json.dumps({
            "status": "error",
            "hostname": hostname,
            "error": "SSH authentication failed"
        }, indent=2)
    except asyncio.TimeoutError:
        return json.dumps({
            "status": "error",
            "hostname": hostname,
            "error": "SSH connection timeout"
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "hostname": hostname,
            "error": str(e)
        }, indent=2)