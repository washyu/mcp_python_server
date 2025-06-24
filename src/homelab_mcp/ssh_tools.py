"""SSH-based tools for system discovery and management."""

import asyncio
import json
from typing import Dict, Any, Optional, cast
import asyncssh


async def ssh_discover_system(
    hostname: str, 
    username: str, 
    password: Optional[str] = None, 
    key_path: Optional[str] = None
) -> str:
    """SSH into a system and gather hardware/system information."""
    try:
        # Connect via SSH
        connect_kwargs = {
            "host": hostname,
            "username": username,
            "known_hosts": None,
            "connect_timeout": 10
        }
        
        if key_path:
            connect_kwargs["client_keys"] = [key_path]
        elif password:
            connect_kwargs["password"] = password
        else:
            raise ValueError("Either password or key_path must be provided")
        
        async with await asyncssh.connect(**connect_kwargs) as conn:
            system_info = {}
            
            # Get actual hostname from the remote system
            hostname_result = await conn.run('hostname', check=False)
            actual_hostname = hostname
            if hostname_result.exit_status == 0 and hostname_result.stdout:
                actual_hostname = cast(str, hostname_result.stdout).strip()
            
            # Get CPU information
            cpu_result = await conn.run('cat /proc/cpuinfo | grep "model name" | head -1 && nproc', check=False)
            if cpu_result.exit_status == 0 and cpu_result.stdout:
                lines = cast(str, cpu_result.stdout).strip().split('\n')
                if len(lines) >= 2:
                    cpu_model = lines[0].split(':', 1)[1].strip() if ':' in lines[0] else "Unknown"
                    cpu_cores = lines[1].strip()
                    system_info['cpu'] = {'model': cpu_model, 'cores': cpu_cores}
            
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