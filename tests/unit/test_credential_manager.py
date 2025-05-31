"""
Unit tests for CredentialManager.
"""

import pytest
import json
from pathlib import Path
from src.utils.credential_manager import (
    CredentialManager, 
    EncryptedFileBackend,
    get_credential_manager
)


class TestEncryptedFileBackend:
    """Test EncryptedFileBackend class."""
    
    @pytest.mark.unit
    def test_init(self, temp_dir):
        """Test backend initialization."""
        backend = EncryptedFileBackend(
            storage_path=temp_dir / "test.enc",
            password="test_password"
        )
        
        assert backend.storage_path == temp_dir / "test.enc"
        assert backend.password == "test_password"
        assert backend.cipher is not None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_set_and_get(self, temp_dir):
        """Test setting and getting credentials."""
        backend = EncryptedFileBackend(
            storage_path=temp_dir / "test.enc",
            password="test_password"
        )
        
        # Set a credential
        await backend.set("test_key", "test_value")
        
        # Get it back
        value = await backend.get("test_key")
        assert value == "test_value"
        
        # Check file exists
        assert backend.storage_path.exists()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete(self, temp_dir):
        """Test deleting credentials."""
        backend = EncryptedFileBackend(
            storage_path=temp_dir / "test.enc",
            password="test_password"
        )
        
        # Set and delete
        await backend.set("test_key", "test_value")
        await backend.delete("test_key")
        
        # Should return None
        value = await backend.get("test_key")
        assert value is None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_keys(self, temp_dir):
        """Test listing credential keys."""
        backend = EncryptedFileBackend(
            storage_path=temp_dir / "test.enc",
            password="test_password"
        )
        
        # Set multiple credentials
        await backend.set("key1", "value1")
        await backend.set("key2", "value2")
        await backend.set("key3", "value3")
        
        # List keys
        keys = await backend.list_keys()
        assert set(keys) == {"key1", "key2", "key3"}
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_encryption(self, temp_dir):
        """Test that data is actually encrypted."""
        backend = EncryptedFileBackend(
            storage_path=temp_dir / "test.enc",
            password="test_password"
        )
        
        # Set a credential
        await backend.set("secret_key", "secret_value")
        
        # Read raw file content
        with open(backend.storage_path, "rb") as f:
            raw_content = f.read()
        
        # Should not contain plaintext
        assert b"secret_key" not in raw_content
        assert b"secret_value" not in raw_content
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_wrong_password(self, temp_dir):
        """Test that wrong password fails to decrypt."""
        storage_path = temp_dir / "test.enc"
        
        # Create with one password
        backend1 = EncryptedFileBackend(
            storage_path=storage_path,
            password="correct_password"
        )
        await backend1.set("test_key", "test_value")
        
        # Try to read with different password
        backend2 = EncryptedFileBackend(
            storage_path=storage_path,
            password="wrong_password"
        )
        
        # Should return empty dict (decryption fails silently)
        value = await backend2.get("test_key")
        assert value is None


class TestCredentialManager:
    """Test CredentialManager class."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_service_namespacing(self, mock_credential_manager):
        """Test that credentials are namespaced by service."""
        cm = mock_credential_manager
        
        # Set credentials for different services
        await cm.set_credential("proxmox", "password", "proxmox_pass")
        await cm.set_credential("ansible", "password", "ansible_pass")
        await cm.set_credential("proxmox", "token", "proxmox_token")
        
        # Get them back
        assert await cm.get_credential("proxmox", "password") == "proxmox_pass"
        assert await cm.get_credential("ansible", "password") == "ansible_pass"
        assert await cm.get_credential("proxmox", "token") == "proxmox_token"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_service_credentials(self, mock_credential_manager):
        """Test getting all credentials for a service."""
        cm = mock_credential_manager
        
        # Set multiple credentials for proxmox
        await cm.set_credential("proxmox", "password", "pass123")
        await cm.set_credential("proxmox", "api_token", "token123")
        await cm.set_credential("proxmox", "username", "root@pam")
        
        # Set one for ansible
        await cm.set_credential("ansible", "vault_pass", "vault123")
        
        # Get all proxmox credentials
        proxmox_creds = await cm.get_service_credentials("proxmox")
        
        assert proxmox_creds == {
            "password": "pass123",
            "api_token": "token123",
            "username": "root@pam"
        }
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_credential(self, mock_credential_manager):
        """Test deleting credentials."""
        cm = mock_credential_manager
        
        # Set and delete
        await cm.set_credential("proxmox", "password", "test123")
        await cm.delete_credential("proxmox", "password")
        
        # Should be None
        value = await cm.get_credential("proxmox", "password")
        assert value is None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_migrate_from_env(self, mock_credential_manager, monkeypatch):
        """Test migrating credentials from environment."""
        cm = mock_credential_manager
        
        # Mock config values
        monkeypatch.setattr("config.Config.PROXMOX_PASSWORD", "env_password")
        monkeypatch.setattr("config.Config.PROXMOX_API_TOKEN", "env_token")
        monkeypatch.setenv("ANSIBLE_VAULT_PASSWORD", "vault_pass")
        
        # Migrate
        migrated = await cm.migrate_from_env()
        
        assert migrated == 3
        
        # Check they were migrated
        assert await cm.get_credential("proxmox", "password") == "env_password"
        assert await cm.get_credential("proxmox", "api_token") == "env_token"
        assert await cm.get_credential("ansible", "vault_password") == "vault_pass"


class TestGlobalInstance:
    """Test global credential manager instance."""
    
    @pytest.mark.unit
    def test_get_credential_manager(self, monkeypatch, temp_dir):
        """Test getting global instance."""
        # Mock the storage path
        monkeypatch.setattr(
            "src.utils.credential_manager.Path.home",
            lambda: temp_dir
        )
        
        # Get instance
        cm1 = get_credential_manager()
        cm2 = get_credential_manager()
        
        # Should be same instance
        assert cm1 is cm2
        assert isinstance(cm1, CredentialManager)