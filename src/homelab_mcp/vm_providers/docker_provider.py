"""Docker VM provider implementation."""

import asyncio
import json
from typing import Dict, List, Optional, Any
import asyncssh

from .base import VMProvider


class DockerVMProvider(VMProvider):
    """Docker container management provider."""
    
    @property
    def platform_name(self) -> str:
        return "docker"
    
    # VM Lifecycle Operations
    async def deploy_vm(
        self, 
        conn: asyncssh.SSHClientConnection,
        vm_name: str,
        vm_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deploy a new Docker container."""
        try:
            ssh_port = vm_config.get("ssh_port", 22)
            external_port = 2222 if ssh_port == 22 else ssh_port
            
            # Clean up existing container
            await self.execute_command(conn, f'docker stop {vm_name} || true')
            await self.execute_command(conn, f'docker rm {vm_name} || true')
            
            # Deploy new container
            commands = [
                f'docker run -d --name {vm_name} --hostname {vm_name} -p {external_port}:22 ubuntu:22.04 sleep infinity',
                'sleep 5',  # Wait for container to start
                f'docker exec {vm_name} apt update',
                f'docker exec {vm_name} apt install -y openssh-server sudo curl htop git',
                f'docker exec {vm_name} service ssh start',
                f'docker exec {vm_name} useradd -m -s /bin/bash -G sudo homelab',
                f'docker exec {vm_name} bash -c "echo \'homelab:homelab123\' | chpasswd"',
                f'docker exec {vm_name} bash -c "echo \'homelab ALL=(ALL) NOPASSWD:ALL\' > /etc/sudoers.d/homelab"',
            ]
            
            for cmd in commands:
                result = await self.execute_command(conn, cmd, timeout=90)
                if result.exit_status != 0 and '||' not in cmd:
                    return self.format_error_response(
                        "deploy", vm_name,
                        f"Deployment failed at: {cmd} - {result.stderr}"
                    )
            
            # Get host IP for external access
            host_ip_result = await self.execute_command(conn, 'hostname -I | awk \'{print $1}\'')
            host_ip = host_ip_result.stdout.strip() if host_ip_result.exit_status == 0 else "unknown"
            
            return self.format_success_response(
                "deploy", vm_name,
                f"Docker container '{vm_name}' deployed successfully",
                ip=host_ip,
                port=external_port,
                ssh_command=f"ssh homelab@{host_ip} -p {external_port}",
                credentials="homelab:homelab123"
            )
            
        except Exception as e:
            return self.format_error_response("deploy", vm_name, str(e))
    
    async def delete_vm(
        self,
        conn: asyncssh.SSHClientConnection, 
        vm_name: str
    ) -> Dict[str, Any]:
        """Delete a Docker container."""
        try:
            stop_result = await self.execute_command(conn, f'docker stop {vm_name}')
            remove_result = await self.execute_command(conn, f'docker rm {vm_name}')
            
            if remove_result.exit_status == 0:
                return self.format_success_response(
                    "delete", vm_name,
                    f"Docker container '{vm_name}' deleted successfully"
                )
            else:
                return self.format_error_response(
                    "delete", vm_name,
                    f"Failed to delete container: {remove_result.stderr}"
                )
                
        except Exception as e:
            return self.format_error_response("delete", vm_name, str(e))
    
    async def list_vms(
        self,
        conn: asyncssh.SSHClientConnection
    ) -> List[Dict[str, Any]]:
        """List all Docker containers."""
        try:
            result = await self.execute_command(
                conn, 
                'docker ps -a --format "{{.Names}}\t{{.Status}}\t{{.Ports}}"'
            )
            
            vms = []
            if result.exit_status == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            name = parts[0]
                            status = parts[1]
                            ports = parts[2] if len(parts) > 2 else ""
                            
                            vms.append({
                                "platform": self.platform_name,
                                "name": name,
                                "status": status,
                                "ports": ports
                            })
            
            return vms
            
        except Exception:
            return []
    
    # VM Control Operations
    async def start_vm(
        self,
        conn: asyncssh.SSHClientConnection,
        vm_name: str
    ) -> Dict[str, Any]:
        """Start a Docker container."""
        try:
            result = await self.execute_command(conn, f'docker start {vm_name}')
            
            if result.exit_status == 0:
                return self.format_success_response(
                    "start", vm_name,
                    f"Docker container '{vm_name}' started successfully"
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
        """Stop a Docker container."""
        try:
            result = await self.execute_command(conn, f'docker stop {vm_name}')
            
            if result.exit_status == 0:
                return self.format_success_response(
                    "stop", vm_name,
                    f"Docker container '{vm_name}' stopped successfully"
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
        """Restart a Docker container."""
        try:
            result = await self.execute_command(conn, f'docker restart {vm_name}')
            
            if result.exit_status == 0:
                return self.format_success_response(
                    "restart", vm_name,
                    f"Docker container '{vm_name}' restarted successfully"
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
        """Get detailed Docker container status."""
        try:
            # Get container info
            inspect_result = await self.execute_command(conn, f'docker inspect {vm_name}')
            if inspect_result.exit_status != 0:
                return self.format_error_response(
                    "status", vm_name,
                    f"Container '{vm_name}' not found"
                )
            
            container_info = json.loads(inspect_result.stdout)[0]
            state = container_info.get('State', {})
            config = container_info.get('Config', {})
            network_settings = container_info.get('NetworkSettings', {})
            
            # Get resource usage stats
            stats_result = await self.execute_command(
                conn,
                f'docker stats {vm_name} --no-stream --format "{{{{.CPUPerc}}}},{{{{.MemUsage}}}},{{{{.NetIO}}}},{{{{.BlockIO}}}}"'
            )
            
            cpu_usage = "N/A"
            memory_usage = "N/A" 
            network_io = "N/A"
            block_io = "N/A"
            
            if stats_result.exit_status == 0 and stats_result.stdout.strip():
                stats_parts = stats_result.stdout.strip().split(',')
                if len(stats_parts) >= 4:
                    cpu_usage = stats_parts[0]
                    memory_usage = stats_parts[1]
                    network_io = stats_parts[2]
                    block_io = stats_parts[3]
            
            return self.format_success_response(
                "status", vm_name,
                f"Docker container '{vm_name}' status retrieved",
                state={
                    "running": state.get('Running', False),
                    "paused": state.get('Paused', False),
                    "restarting": state.get('Restarting', False),
                    "status": state.get('Status', 'unknown'),
                    "started_at": state.get('StartedAt', 'unknown'),
                    "finished_at": state.get('FinishedAt', 'unknown'),
                    "exit_code": state.get('ExitCode', 0)
                },
                resource_usage={
                    "cpu_percent": cpu_usage,
                    "memory_usage": memory_usage,
                    "network_io": network_io,
                    "block_io": block_io
                },
                config={
                    "image": config.get('Image', 'unknown'),
                    "hostname": config.get('Hostname', 'unknown'),
                    "exposed_ports": list(config.get('ExposedPorts', {}).keys()),
                    "env_vars": len(config.get('Env', []))
                },
                network={
                    "ip_address": network_settings.get('IPAddress', ''),
                    "ports": network_settings.get('Ports', {})
                }
            )
            
        except json.JSONDecodeError:
            return self.format_error_response(
                "status", vm_name,
                "Failed to parse container information"
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
        """Get Docker container logs."""
        try:
            cmd = f'docker logs --tail {lines}'
            if follow:
                cmd += ' -f'
            cmd += f' {vm_name}'
            
            # For follow mode, limit time to avoid hanging
            timeout = 10 if follow else 30
            result = await self.execute_command(conn, cmd, timeout=timeout)
            
            if result.exit_status == 0:
                logs = result.stdout if result.stdout else "No logs available"
                return self.format_success_response(
                    "logs", vm_name,
                    f"Retrieved logs for container '{vm_name}'",
                    logs=logs,
                    lines_requested=lines,
                    follow_mode=follow
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
        """List services running inside Docker container."""
        try:
            # Try systemctl first
            result = await self.execute_command(
                conn,
                f'docker exec {vm_name} systemctl list-units --type=service --no-pager'
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
                # Fallback to ps if systemctl not available
                ps_result = await self.execute_command(conn, f'docker exec {vm_name} ps aux')
                if ps_result.exit_status == 0:
                    return self.format_success_response(
                        "list_services", vm_name,
                        "systemctl not available, showing running processes",
                        processes=ps_result.stdout,
                        note="Process list instead of services"
                    )
                else:
                    return self.format_error_response(
                        "list_services", vm_name,
                        "Unable to list services or processes"
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
        """Control a specific service inside Docker container."""
        try:
            result = await self.execute_command(
                conn,
                f'docker exec {vm_name} systemctl {action} {service_name}'
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