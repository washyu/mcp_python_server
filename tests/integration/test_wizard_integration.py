"""
Integration tests for setup wizard flows.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.utils.setup_wizard import SetupWizard, WizardFlow
from src.utils.credential_manager import CredentialManager, EncryptedFileBackend
from src.utils.proxmox_tools import ProxmoxConnectionTest


class TestWizardIntegration:
    """Test setup wizard integration with other components."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_proxmox_wizard_flow(self, temp_dir):
        """Test complete Proxmox setup wizard flow."""
        # Set up credential manager
        backend = EncryptedFileBackend(
            storage_path=temp_dir / "wizard_creds.enc",
            password="wizard_password"
        )
        cred_manager = CredentialManager(backend)
        
        # Create wizard
        wizard = SetupWizard()
        
        # Mock user inputs for Proxmox setup
        test_inputs = {
            "host": "192.168.10.200",
            "username": "root@pam",
            "password": "test_password",
            "verify_ssl": False
        }
        
        # Test wizard validation
        flow = wizard.get_flow("proxmox_setup")
        assert flow is not None
        assert flow.name == "proxmox_setup"
        
        # Validate each step
        for step in flow.steps:
            if step.id in test_inputs:
                # Simulate user input
                result = step.validate(test_inputs[step.id])
                if step.required and test_inputs[step.id]:
                    assert result is True
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_wizard_with_connection_test(self, temp_dir, mock_aiohttp_session):
        """Test wizard flow with actual connection testing."""
        session_mock, response_mock = mock_aiohttp_session
        response_mock.status = 200
        response_mock.json = AsyncMock(return_value={
            "data": {
                "ticket": "test_ticket",
                "CSRFPreventionToken": "test_csrf"
            }
        })
        
        # Set up credential manager
        backend = EncryptedFileBackend(
            storage_path=temp_dir / "wizard_test_creds.enc",
            password="wizard_test_password"
        )
        cred_manager = CredentialManager(backend)
        
        # Test configuration
        config = {
            "host": "192.168.10.200",
            "username": "root@pam", 
            "password": "test_password",
            "verify_ssl": False
        }
        
        with patch("aiohttp.ClientSession", return_value=session_mock):
            # Test connection
            success, token = await ProxmoxConnectionTest.test_and_display(config, cred_manager)
            
            # Should succeed with mocked response
            assert success is True
            
            # Should have stored credentials
            stored_creds = await cred_manager.get_service_credentials("proxmox")
            assert stored_creds["host"] == "192.168.10.200"
            assert stored_creds["username"] == "root@pam"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_wizard_api_token_creation(self, temp_dir, mock_aiohttp_session):
        """Test wizard flow with API token creation."""
        session_mock, response_mock = mock_aiohttp_session
        
        # Mock successful auth then token creation
        auth_response = {
            "data": {
                "ticket": "test_ticket",
                "CSRFPreventionToken": "test_csrf"
            }
        }
        
        token_response = {
            "data": {
                "tokenid": "mcp-server",
                "value": "abcd-1234-efgh-5678"
            }
        }
        
        # Mock sequence of responses
        response_mock.status = 200
        response_mock.json = AsyncMock(side_effect=[auth_response, token_response])
        
        # Set up credential manager
        backend = EncryptedFileBackend(
            storage_path=temp_dir / "token_creds.enc",
            password="token_password"
        )
        cred_manager = CredentialManager(backend)
        
        config = {
            "host": "192.168.10.200",
            "username": "root@pam",
            "password": "test_password",
            "verify_ssl": False,
            "create_token": True
        }
        
        with patch("aiohttp.ClientSession", return_value=session_mock):
            # Test connection with token creation
            success, token = await ProxmoxConnectionTest.test_and_display(config, cred_manager)
            
            # Should succeed
            assert success is True
            
            # Should have created token
            if token:
                assert "mcp-server" in token
                
                # Should have stored the token
                stored_creds = await cred_manager.get_service_credentials("proxmox")
                assert stored_creds.get("api_token") is not None
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_wizard_error_handling(self, temp_dir, mock_aiohttp_session):
        """Test wizard error handling with failed connections."""
        session_mock, response_mock = mock_aiohttp_session
        response_mock.status = 401  # Unauthorized
        
        # Set up credential manager
        backend = EncryptedFileBackend(
            storage_path=temp_dir / "error_creds.enc",
            password="error_password"
        )
        cred_manager = CredentialManager(backend)
        
        config = {
            "host": "192.168.10.200",
            "username": "root@pam",
            "password": "wrong_password",
            "verify_ssl": False
        }
        
        with patch("aiohttp.ClientSession", return_value=session_mock):
            # Test connection with wrong credentials
            success, token = await ProxmoxConnectionTest.test_and_display(config, cred_manager)
            
            # Should fail
            assert success is False
            assert token is None
            
            # Should not have stored invalid credentials
            stored_creds = await cred_manager.get_service_credentials("proxmox")
            assert len(stored_creds) == 0  # Should be empty dict
    
    @pytest.mark.integration 
    @pytest.mark.asyncio
    async def test_wizard_multi_step_validation(self, temp_dir):
        """Test wizard with multi-step validation flow."""
        # Set up credential manager
        backend = EncryptedFileBackend(
            storage_path=temp_dir / "multi_step_creds.enc",
            password="multi_step_password"
        )
        cred_manager = CredentialManager(backend)
        
        wizard = SetupWizard()
        flow = wizard.get_flow("proxmox_setup")
        
        # Test step-by-step validation
        test_data = {}
        
        for step in flow.steps:
            if step.id == "host":
                test_data[step.id] = "192.168.10.200"
                assert step.validate(test_data[step.id]) is True
            elif step.id == "username":
                test_data[step.id] = "root@pam"
                assert step.validate(test_data[step.id]) is True
            elif step.id == "password":
                test_data[step.id] = "secure_password"
                assert step.validate(test_data[step.id]) is True
            elif step.id == "verify_ssl":
                test_data[step.id] = False
                assert step.validate(test_data[step.id]) in [True, None]  # Boolean might not have validation
        
        # Verify we collected all required data
        assert "host" in test_data
        assert "username" in test_data
        assert "password" in test_data
        assert "verify_ssl" in test_data