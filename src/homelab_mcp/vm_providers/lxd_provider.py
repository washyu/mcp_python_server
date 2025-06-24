"""LXD VM provider implementation."""

import asyncio
import json
from typing import Dict, List, Optional, Any
import asyncssh

from .base import VMProvider


class LXDVMProvider(VMProvider):
    """LXD container management provider."""
    
    @property
    def platform_name(self) -> str:
        return "lxd"
    
    # VM Lifecycle Operations
    async def deploy_vm(
        self, 
        conn: asyncssh.SSHClientConnection,
        vm_name: str,
        vm_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deploy a new LXD container."""
        try:
            # Clean up existing container
            await self.execute_command(conn, f'sudo lxc stop {vm_name} --force || true')
            await self.execute_command(conn, f'sudo lxc delete {vm_name} || true')
            
            # Launch container
            launch_result = await self.execute_command(
                conn, 
                f'sudo lxc launch ubuntu:22.04 {vm_name}',
                timeout=120
            )
            
            if launch_result.exit_status != 0:
                return self.format_error_response(
                    "deploy", vm_name,
                    f"LXD launch failed: {launch_result.stderr}"
                )
            
            # Wait for container to be ready
            await asyncio.sleep(15)
            
            # Configure container
            commands = [
                f'sudo lxc exec {vm_name} -- apt update',
                f'sudo lxc exec {vm_name} -- apt install -y openssh-server sudo curl htop git',
                f'sudo lxc exec {vm_name} -- systemctl enable ssh',
                f'sudo lxc exec {vm_name} -- systemctl start ssh',
                f'sudo lxc exec {vm_name} -- useradd -m -s /bin/bash -G sudo homelab',
                f'sudo lxc exec {vm_name} -- bash -c "echo \'homelab:homelab123\' | chpasswd"',
                f'sudo lxc exec {vm_name} -- bash -c "echo \'homelab ALL=(ALL) NOPASSWD:ALL\' > /etc/sudoers.d/homelab"',
            ]
            
            for cmd in commands:
                result = await self.execute_command(conn, cmd, timeout=60)
                if result.exit_status != 0:
                    return self.format_error_response(
                        "deploy", vm_name,
                        f"LXD configuration failed: {result.stderr}"
                    )
            
            # Get container IP
            vm_ip = await self._get_container_ip(conn, vm_name)
            
            return self.format_success_response(
                "deploy", vm_name,
                f"LXD container '{vm_name}' deployed successfully",
                ip=vm_ip,
                port=22,
                ssh_command=f"ssh homelab@{vm_ip}" if vm_ip else "IP not available",
                credentials="homelab:homelab123"
            )
            
        except Exception as e:
            return self.format_error_response("deploy", vm_name, str(e))
    
    async def delete_vm(
        self,
        conn: asyncssh.SSHClientConnection, 
        vm_name: str
    ) -> Dict[str, Any]:
        """Delete an LXD container."""
        try:
            stop_result = await self.execute_command(conn, f'sudo lxc stop {vm_name} --force')
            delete_result = await self.execute_command(conn, f'sudo lxc delete {vm_name}')
            
            if delete_result.exit_status == 0:
                return self.format_success_response(
                    "delete", vm_name,
                    f"LXD container '{vm_name}' deleted successfully"
                )
            else:
                return self.format_error_response(
                    "delete", vm_name,
                    f"Failed to delete container: {delete_result.stderr}"
                )
                
        except Exception as e:
            return self.format_error_response("delete", vm_name, str(e))
    
    async def list_vms(
        self,
        conn: asyncssh.SSHClientConnection
    ) -> List[Dict[str, Any]]:
        """List all LXD containers."""
        try:
            result = await self.execute_command(conn, 'sudo lxc list --format json')
            
            vms = []
            if result.exit_status == 0:
                try:
                    containers = json.loads(result.stdout)
                    for container in containers:
                        name = container.get('name', 'unknown')
                        status = container.get('status', 'unknown')
                        
                        # Get IP address
                        ip = None
                        if container.get('state', {}).get('network', {}):
                            for interface, details in container['state']['network'].items():
                                if interface != 'lo':
                                    addresses = details.get('addresses', [])
                                    for addr in addresses:
                                        if addr.get('family') == 'inet':
                                            ip = addr.get('address')
                                            break
                                    if ip:
                                        break
                        
                        vms.append({
                            "platform": self.platform_name,
                            "name": name,
                            "status": status,
                            "ip": ip
                        })
                except json.JSONDecodeError:
                    pass
            
            return vms
            
        except Exception:
            return []
    
    # VM Control Operations
    async def start_vm(
        self,
        conn: asyncssh.SSHClientConnection,
        vm_name: str
    ) -> Dict[str, Any]:
        """Start an LXD container."""
        try:
            result = await self.execute_command(conn, f'sudo lxc start {vm_name}')
            
            if result.exit_status == 0:
                return self.format_success_response(
                    "start", vm_name,
                    f"LXD container '{vm_name}' started successfully"
                )
            else:
                return self.format_error_response(
                    "start", vm_name,
                    f"Failed to start container: {result.stderr}"
                )
                
        except Exception as e:
            return self.format_error_response("start", vm_name, str(e))
    
    async def stop_vm(
        self,
        conn: asyncssh.SSHClientConnection,
        vm_name: str
    ) -> Dict[str, Any]:
        """Stop an LXD container."""
        try:
            result = await self.execute_command(conn, f'sudo lxc stop {vm_name}')
            
            if result.exit_status == 0:
                return self.format_success_response(
                    "stop", vm_name,
                    f"LXD container '{vm_name}' stopped successfully"
                )
            else:
                return self.format_error_response(
                    "stop", vm_name,
                    f"Failed to stop container: {result.stderr}"
                )
                
        except Exception as e:
            return self.format_error_response("stop", vm_name, str(e))
    
    async def restart_vm(
        self,
        conn: asyncssh.SSHClientConnection,
        vm_name: str
    ) -> Dict[str, Any]:
        """Restart an LXD container."""
        try:
            result = await self.execute_command(conn, f'sudo lxc restart {vm_name}')
            
            if result.exit_status == 0:
                return self.format_success_response(
                    "restart", vm_name,
                    f"LXD container '{vm_name}' restarted successfully"
                )
            else:
                return self.format_error_response(
                    "restart", vm_name,
                    f"Failed to restart container: {result.stderr}"
                )
                
        except Exception as e:
            return self.format_error_response("restart", vm_name, str(e))
    
    # VM Monitoring Operations
    async def get_vm_status(
        self,
        conn: asyncssh.SSHClientConnection,
        vm_name: str
    ) -> Dict[str, Any]:
        """Get detailed LXD container status."""
        try:
            # Get container info
            info_result = await self.execute_command(conn, f'sudo lxc info {vm_name}')
            if info_result.exit_status != 0:
                return self.format_error_response(
                    "status", vm_name,
                    f"Container '{vm_name}' not found"
                )
            
            # Parse LXD info output
            info_lines = info_result.stdout.split('\n')
            container_status = {}
            resource_usage = {}
            network_info = {}
            
            current_section = None
            for line in info_lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.endswith(':') and not line.startswith(' '):
                    current_section = line[:-1].lower().replace(' ', '_')
                    continue
                
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    
                    if current_section == 'general':
                        container_status[key] = value
                    elif current_section == 'resources':
                        resource_usage[key] = value
                    elif current_section == 'network':
                        network_info[key] = value
            
            # Get additional stats
            stats_result = await self.execute_command(conn, f'sudo lxc list {vm_name} --format json')
            container_json = {}
            if stats_result.exit_status == 0:
                try:
                    containers = json.loads(stats_result.stdout)
                    if containers:
                        container_json = containers[0]
                except json.JSONDecodeError:
                    pass
            
            return self.format_success_response(
                "status", vm_name,
                f"LXD container '{vm_name}' status retrieved",
                state={
                    "status": container_status.get('status', 'unknown'),
                    "type": container_status.get('type', 'unknown'),
                    "architecture": container_status.get('architecture', 'unknown'),
                    "created": container_status.get('created', 'unknown'),
                    "pid": container_status.get('pid', 'unknown')
                },
                resource_usage=resource_usage,
                network=network_info,
                container_info=container_json.get('state', {})
            )
            
        except Exception as e:
            return self.format_error_response("status", vm_name, str(e))
    
    async def get_vm_logs(
        self,
        conn: asyncssh.SSHClientConnection,
        vm_name: str,
        lines: int = 50,
        follow: bool = False
    ) -> Dict[str, Any]:
        """Get LXD container logs."""
        try:
            # LXD doesn't have direct log commands like Docker, so we'll get system logs
            cmd = f'sudo lxc exec {vm_name} -- journalctl -n {lines}'
            if follow:
                cmd += ' -f'
            
            timeout = 10 if follow else 30
            result = await self.execute_command(conn, cmd, timeout=timeout)
            
            if result.exit_status == 0:
                logs = result.stdout if result.stdout else "No logs available"
                return self.format_success_response(
                    "logs", vm_name,
                    f"Retrieved logs for container '{vm_name}'",
                    logs=logs,
                    lines_requested=lines,
                    follow_mode=follow,
                    note="Showing system journal logs from inside container"
                )
            else:
                # Fallback to dmesg if journalctl not available
                dmesg_result = await self.execute_command(
                    conn, 
                    f'sudo lxc exec {vm_name} -- dmesg | tail -{lines}'
                )
                if dmesg_result.exit_status == 0:
                    return self.format_success_response(
                        "logs", vm_name,
                        f"Retrieved kernel logs for container '{vm_name}'",
                        logs=dmesg_result.stdout,
                        lines_requested=lines,
                        follow_mode=False,
                        note="Showing kernel messages (dmesg) as fallback"
                    )
                else:
                    return self.format_error_response(
                        "logs", vm_name,
                        f"Failed to get logs: {result.stderr}"
                    )
                    
        except Exception as e:
            return self.format_error_response("logs", vm_name, str(e))
    
    # Service Management Operations
    async def list_vm_services(
        self,
        conn: asyncssh.SSHClientConnection,
        vm_name: str
    ) -> Dict[str, Any]:
        """List services running inside LXD container."""
        try:
            result = await self.execute_command(
                conn,
                f'sudo lxc exec {vm_name} -- systemctl list-units --type=service --no-pager'
            )
            
            if result.exit_status == 0:
                services = []
                for line in result.stdout.split('\n')[1:]:  # Skip header
                    if line.strip() and not line.startswith('●') and 'service' in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            services.append({
                                "name": parts[0].replace('.service', ''),
                                "load": parts[1],
                                "active": parts[2],
                                "sub": parts[3],
                                "description": ' '.join(parts[4:]) if len(parts) > 4 else ""
                            })
                
                return self.format_success_response(
                    "list_services", vm_name,
                    f"Listed services for container '{vm_name}'",
                    services=services,
                    total_services=len(services)
                )
            else:
                return self.format_error_response(
                    "list_services", vm_name,
                    f"Failed to list services: {result.stderr}"
                )
                
        except Exception as e:
            return self.format_error_response("list_services", vm_name, str(e))
    
    async def control_vm_service(
        self,
        conn: asyncssh.SSHClientConnection,
        vm_name: str,
        service_name: str,
        action: str
    ) -> Dict[str, Any]:
        """Control a specific service inside LXD container."""
        try:
            result = await self.execute_command(
                conn,
                f'sudo lxc exec {vm_name} -- systemctl {action} {service_name}'
            )
            
            if result.exit_status == 0:
                return self.format_success_response(
                    f"service_{action}", vm_name,
                    f"Service '{service_name}' {action} successful",
                    service_name=service_name,
                    action=action,
                    output=result.stdout if result.stdout else "No output"
                )
            else:
                return self.format_error_response(
                    f"service_{action}", vm_name,
                    f"Service {action} failed: {result.stderr}",
                    service_name=service_name,
                    action=action
                )
                
        except Exception as e:
            return self.format_error_response(
                f"service_{action}", vm_name, str(e),
                service_name=service_name,
                action=action
            )
    
    # Helper Methods
    async def _get_container_ip(
        self,
        conn: asyncssh.SSHClientConnection,
        vm_name: str
    ) -> Optional[str]:
        """Get the IP address of an LXD container."""
        try:
            result = await self.execute_command(conn, f'sudo lxc list {vm_name} --format json')
            if result.exit_status == 0:
                containers = json.loads(result.stdout)
                if containers:
                    container = containers[0]
                    if container.get('state', {}).get('network', {}):
                        for interface, details in container['state']['network'].items():
                            if interface != 'lo':
                                addresses = details.get('addresses', [])
                                for addr in addresses:
                                    if addr.get('family') == 'inet':
                                        return addr.get('address')
        except (json.JSONDecodeError, Exception):
            pass
        
        return None