"""
Integration test for VM creation through MCP interface.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.server.mcp_server import ProxmoxMCPServer
from src.tools.vm_creation import VMCreationRequest, VMCreationResult


@pytest.mark.asyncio
async def test_vm_creation_tool_registration():
    """Test that VM creation tools are properly registered in MCP server."""
    with patch('src.utils.credential_manager.get_credential_manager') as mock_get_cm:
        mock_cm = AsyncMock()
        mock_get_cm.return_value = mock_cm
        mock_cm.get_service_credentials = AsyncMock(return_value={
            "host": "192.168.10.200",
            "username": "root@pam",
            "password": "test_password",
            "verify_ssl": False
        })
        
        server = ProxmoxMCPServer()
        
        # Check that all VM management tools are registered by checking the handlers
        assert hasattr(server, '_create_vm_handler')
        assert hasattr(server, '_start_vm_handler')
        assert hasattr(server, '_stop_vm_handler')
        assert hasattr(server, '_delete_vm_handler')
        assert hasattr(server, '_get_vm_status_handler')


@pytest.mark.asyncio
async def test_create_vm_handler():
    """Test the create_vm handler through MCP interface."""
    with patch('src.utils.credential_manager.get_credential_manager') as mock_get_cm:
        mock_cm = AsyncMock()
        mock_get_cm.return_value = mock_cm
        mock_cm.get_service_credentials = AsyncMock(return_value={
            "host": "192.168.10.200",
            "username": "root@pam",
            "password": "test_password",
            "verify_ssl": False
        })
        
        server = ProxmoxMCPServer()
        
        # Mock the VM creation
        mock_result = VMCreationResult(
            vm_id=201,
            name="test-vm",
            node="proxmox",
            ip_address="192.168.10.201",
            ssh_user="ansible-admin",
            status="running",
            services=["qemu-guest-agent", "docker"]
        )
        
        with patch('src.tools.vm_creation.ProxmoxVMCreator') as mock_creator_class:
            mock_creator = AsyncMock()
            mock_creator_class.return_value = mock_creator
            mock_creator.ensure_client = AsyncMock()
            mock_creator.create_vm = AsyncMock(return_value=mock_result)
            
            # Call the handler
            result = await server._create_vm_handler(
                name="test-vm",
                cores=2,
                memory_gb=4,
                install_docker=True
            )
            
            # Verify the response
            assert len(result) == 1
            assert result[0].type == "text"
            assert "✅" in result[0].text
            assert "VM ID: 201" in result[0].text
            assert "Node: proxmox" in result[0].text
            assert "192.168.10.201" in result[0].text


@pytest.mark.asyncio
async def test_vm_lifecycle_handlers():
    """Test VM lifecycle management handlers."""
    with patch('src.utils.credential_manager.get_credential_manager') as mock_get_cm:
        mock_cm = AsyncMock()
        mock_get_cm.return_value = mock_cm
        mock_cm.get_service_credentials = AsyncMock(return_value={
            "host": "192.168.10.200",
            "username": "root@pam",
            "password": "test_password",
            "verify_ssl": False
        })
        
        server = ProxmoxMCPServer()
        
        with patch('src.tools.vm_creation.ProxmoxVMCreator') as mock_creator_class:
            mock_creator = AsyncMock()
            mock_creator_class.return_value = mock_creator
            mock_creator.ensure_client = AsyncMock()
            mock_creator.client = AsyncMock()
            
            # Test start_vm
            mock_creator.client._make_request = AsyncMock(side_effect=[
                {"data": [{"type": "qemu", "vmid": 201, "node": "proxmox"}]},  # Find VM
                {"data": "OK"}  # Start response
            ])
            
            result = await server._start_vm_handler(vm_id=201)
            assert "✅" in result[0].text
            assert "VM 201 started successfully" in result[0].text
            
            # Test stop_vm
            mock_creator.client._make_request = AsyncMock(side_effect=[
                {"data": [{"type": "qemu", "vmid": 201, "node": "proxmox"}]},  # Find VM
                {"data": "OK"}  # Stop response
            ])
            
            result = await server._stop_vm_handler(vm_id=201)
            assert "✅" in result[0].text
            assert "shutdown" in result[0].text
            
            # Test get_vm_status
            mock_creator.client._make_request = AsyncMock(side_effect=[
                {"data": [{"type": "qemu", "vmid": 201, "node": "proxmox", "name": "test-vm", 
                          "status": "running", "cpu": 0.15, "mem": 2147483648, "maxmem": 4294967296}]},  # Find VM
                {"data": {"cores": 2, "memory": 4096}}  # Config
            ])
            mock_creator._get_vm_ip = AsyncMock(return_value="192.168.10.201")
            
            result = await server._get_vm_status_handler(vm_id=201)
            assert "VM 201 Status:" in result[0].text
            assert "Status: running" in result[0].text
            assert "test-vm" in result[0].text


@pytest.mark.asyncio
async def test_vm_creation_error_handling():
    """Test error handling in VM creation."""
    with patch('src.utils.credential_manager.get_credential_manager') as mock_get_cm:
        mock_cm = AsyncMock()
        mock_get_cm.return_value = mock_cm
        mock_cm.get_service_credentials = AsyncMock(return_value={
            "host": "192.168.10.200",
            "username": "root@pam",
            "password": "test_password",
            "verify_ssl": False
        })
        
        server = ProxmoxMCPServer()
        
        with patch('src.tools.vm_creation.create_vm_tool') as mock_create_vm:
            mock_create_vm.side_effect = ValueError("No Proxmox credentials")
            
            result = await server._create_vm_handler(name="fail-vm")
            
            assert "❌" in result[0].text
            assert "Failed to create VM" in result[0].text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])