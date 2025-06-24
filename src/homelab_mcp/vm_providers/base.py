"""Abstract base class for VM providers."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import asyncio
import asyncssh


class VMProvider(ABC):
    """Abstract base class for platform-specific VM operations."""
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform name (e.g., 'docker', 'lxd', 'proxmox')."""
        pass
    
    # VM Lifecycle Operations
    @abstractmethod
    async def deploy_vm(
        self, 
        conn: asyncssh.SSHClientConnection,
        vm_name: str,
        vm_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deploy a new VM/container."""
        pass
    
    @abstractmethod
    async def delete_vm(
        self,
        conn: asyncssh.SSHClientConnection, 
        vm_name: str
    ) -> Dict[str, Any]:
        """Delete a VM/container."""
        pass
    
    @abstractmethod
    async def list_vms(
        self,
        conn: asyncssh.SSHClientConnection
    ) -> List[Dict[str, Any]]:
        """List all VMs/containers on the host."""
        pass
    
    # VM Control Operations
    @abstractmethod
    async def start_vm(
        self,
        conn: asyncssh.SSHClientConnection,
        vm_name: str
    ) -> Dict[str, Any]:
        """Start a VM/container."""
        pass
    
    @abstractmethod
    async def stop_vm(
        self,
        conn: asyncssh.SSHClientConnection,
        vm_name: str
    ) -> Dict[str, Any]:
        """Stop a VM/container."""
        pass
    
    @abstractmethod
    async def restart_vm(
        self,
        conn: asyncssh.SSHClientConnection,
        vm_name: str
    ) -> Dict[str, Any]:
        """Restart a VM/container."""
        pass
    
    # VM Monitoring Operations
    @abstractmethod
    async def get_vm_status(
        self,
        conn: asyncssh.SSHClientConnection,
        vm_name: str
    ) -> Dict[str, Any]:
        """Get detailed status and resource usage for a VM/container."""
        pass
    
    @abstractmethod
    async def get_vm_logs(
        self,
        conn: asyncssh.SSHClientConnection,
        vm_name: str,
        lines: int = 50,
        follow: bool = False
    ) -> Dict[str, Any]:
        """Get logs from a VM/container."""
        pass
    
    # Service Management Operations
    @abstractmethod
    async def list_vm_services(
        self,
        conn: asyncssh.SSHClientConnection,
        vm_name: str
    ) -> Dict[str, Any]:
        """List services running inside a VM/container."""
        pass
    
    @abstractmethod
    async def control_vm_service(
        self,
        conn: asyncssh.SSHClientConnection,
        vm_name: str,
        service_name: str,
        action: str  # start, stop, restart, status
    ) -> Dict[str, Any]:
        """Control a specific service inside a VM/container."""
        pass
    
    # Utility Methods (can be overridden by providers)
    def validate_vm_name(self, vm_name: str) -> bool:
        """Validate VM name format (can be overridden by providers)."""
        if not vm_name or not isinstance(vm_name, str):
            return False
        # Basic validation - alphanumeric, hyphens, underscores
        return all(c.isalnum() or c in '-_' for c in vm_name)
    
    def format_success_response(
        self, 
        operation: str,
        vm_name: str,
        message: str,
        **extra_data
    ) -> Dict[str, Any]:
        """Format a standard success response."""
        response = {
            "status": "success",
            "platform": self.platform_name,
            "vm_name": vm_name,
            "operation": operation,
            "message": message
        }
        response.update(extra_data)
        return response
    
    def format_error_response(
        self,
        operation: str,
        vm_name: str,
        error_message: str,
        **extra_data
    ) -> Dict[str, Any]:
        """Format a standard error response."""
        response = {
            "status": "error",
            "platform": self.platform_name,
            "vm_name": vm_name,
            "operation": operation,
            "message": error_message
        }
        response.update(extra_data)
        return response
    
    async def execute_command(
        self,
        conn: asyncssh.SSHClientConnection,
        command: str,
        timeout: int = 30,
        check: bool = False
    ) -> asyncssh.SSHCompletedProcess:
        """Execute a command with standardized error handling."""
        try:
            result = await conn.run(command, check=check, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            raise Exception(f"Command timed out after {timeout}s: {command}")
        except Exception as e:
            raise Exception(f"Command execution failed: {command} - {str(e)}")
    
    # Control operations dispatcher
    async def control_vm(
        self,
        conn: asyncssh.SSHClientConnection,
        vm_name: str,
        action: str
    ) -> Dict[str, Any]:
        """Control VM state with action dispatcher."""
        if not self.validate_vm_name(vm_name):
            return self.format_error_response(
                "control", vm_name, 
                f"Invalid VM name: {vm_name}"
            )
        
        if action == "start":
            return await self.start_vm(conn, vm_name)
        elif action == "stop":
            return await self.stop_vm(conn, vm_name)
        elif action == "restart":
            return await self.restart_vm(conn, vm_name)
        else:
            return self.format_error_response(
                "control", vm_name,
                f"Unknown action: {action}. Supported: start, stop, restart"
            )
    
    # Service management dispatcher
    async def manage_vm_services(
        self,
        conn: asyncssh.SSHClientConnection,
        vm_name: str,
        action: str,
        service_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Manage VM services with action dispatcher."""
        if not self.validate_vm_name(vm_name):
            return self.format_error_response(
                "service_management", vm_name,
                f"Invalid VM name: {vm_name}"
            )
        
        if action == "list":
            return await self.list_vm_services(conn, vm_name)
        elif action in ["start", "stop", "restart", "status"]:
            if not service_name:
                return self.format_error_response(
                    "service_management", vm_name,
                    f"Service name required for {action} action"
                )
            return await self.control_vm_service(conn, vm_name, service_name, action)
        else:
            return self.format_error_response(
                "service_management", vm_name,
                f"Unknown action: {action}. Supported: list, start, stop, restart, status"
            )