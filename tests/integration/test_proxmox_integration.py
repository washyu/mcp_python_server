"""
Integration tests for Proxmox API with credential manager.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.utils.proxmox_api import ProxmoxAPIClient
from src.utils.credential_manager import CredentialManager, EncryptedFileBackend
# from src.tools.proxmox_discovery import ProxmoxDiscoveryTools  # Skip for now due to MCP import issues


class TestProxmoxIntegration:
    """Test Proxmox API with credential manager integration."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_proxmox_with_credential_manager(self, temp_dir, mock_proxmox_response):
        """Test ProxmoxAPIClient using credentials from CredentialManager."""
        # Set up credential manager
        backend = EncryptedFileBackend(
            storage_path=temp_dir / "test_creds.enc",
            password="test_password"
        )
        cred_manager = CredentialManager(backend)
        
        # Store test credentials
        await cred_manager.set_credential("proxmox", "host", "192.168.10.200")
        await cred_manager.set_credential("proxmox", "api_token", "root@pam!test=1234")
        
        # Retrieve credentials
        proxmox_creds = await cred_manager.get_service_credentials("proxmox")
        
        # Create API client with retrieved credentials
        client = ProxmoxAPIClient(
            host=proxmox_creds["host"],
            api_token=proxmox_creds["api_token"],
            verify_ssl=False
        )
        
        # Test authentication
        result = await client.authenticate()
        assert result is True  # Token auth always returns True
    
    # TODO: Re-enable when MCP Tool import is fixed
    # @pytest.mark.integration
    # @pytest.mark.asyncio
    # async def test_discovery_tools_with_api_client(self, temp_dir, mock_aiohttp_session, mock_proxmox_response):
    #     """Test discovery tools using API client."""
    #     # Skip for now due to MCP import issues
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_credential_migration_flow(self, temp_dir, monkeypatch):
        """Test migrating credentials from environment to encrypted storage."""
        # Mock environment variables
        monkeypatch.setenv("PROXMOX_HOST", "192.168.10.200")
        monkeypatch.setenv("PROXMOX_API_TOKEN", "root@pam!token=abcd1234")
        
        # Set up credential manager
        backend = EncryptedFileBackend(
            storage_path=temp_dir / "migrated_creds.enc",
            password="migration_password"
        )
        cred_manager = CredentialManager(backend)
        
        # Migrate from environment
        migrated_count = await cred_manager.migrate_from_env()
        
        # Should have migrated some credentials
        assert migrated_count > 0
        
        # Verify migrated credentials
        proxmox_creds = await cred_manager.get_service_credentials("proxmox")
        assert proxmox_creds["host"] == "192.168.10.200"
        assert proxmox_creds["api_token"] == "root@pam!token=abcd1234"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_proxmox_workflow(self, temp_dir, mock_aiohttp_session, mock_proxmox_response):
        """Test complete workflow: store credentials -> create client -> discover resources."""
        session_mock, response_mock = mock_aiohttp_session
        response_mock.status = 200
        response_mock.json = AsyncMock(return_value=mock_proxmox_response["nodes"])
        
        # 1. Set up credential manager
        backend = EncryptedFileBackend(
            storage_path=temp_dir / "workflow_creds.enc",
            password="workflow_password"
        )
        cred_manager = CredentialManager(backend)
        
        # 2. Store credentials (simulating wizard flow)
        await cred_manager.set_credential("proxmox", "host", "192.168.10.200")
        await cred_manager.set_credential("proxmox", "username", "root@pam")
        await cred_manager.set_credential("proxmox", "api_token", "root@pam!test=secret123")
        
        # 3. Retrieve and validate credentials
        creds = await cred_manager.get_service_credentials("proxmox")
        assert creds["host"] == "192.168.10.200"
        assert creds["username"] == "root@pam"
        assert creds["api_token"] == "root@pam!test=secret123"
        
        # 4. Create API client
        client = ProxmoxAPIClient(
            host=creds["host"],
            api_token=creds["api_token"],
            verify_ssl=False
        )
        
        # 5. Test authentication
        auth_result = await client.authenticate()
        assert auth_result is True
        
        # 6. Test discovery
        with patch("aiohttp.ClientSession", return_value=session_mock):
            nodes = await client.list_nodes()
            assert len(nodes) == 1
            assert nodes[0].node == "proxmox"
            assert nodes[0].status == "online"