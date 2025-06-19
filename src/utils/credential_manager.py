"""
Secure credential management for MCP server.
Provides abstraction layer for credential storage with multiple backends.
"""

import os
import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional, Protocol
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import aiofiles
import logging

logger = logging.getLogger(__name__)


class CredentialBackend(Protocol):
    """Protocol for credential storage backends."""
    
    async def get(self, key: str) -> Optional[str]:
        """Get a credential value."""
        ...
    
    async def set(self, key: str, value: str) -> None:
        """Set a credential value."""
        ...
    
    async def delete(self, key: str) -> None:
        """Delete a credential."""
        ...
    
    async def list_keys(self) -> list[str]:
        """List all credential keys."""
        ...


class EncryptedFileBackend:
    """Encrypted file-based credential storage."""
    
    def __init__(self, storage_path: Path = None, password: str = None):
        """
        Initialize encrypted file backend.
        
        Args:
            storage_path: Path to store encrypted credentials
            password: Master password for encryption (uses env var if not provided)
        """
        self.storage_path = storage_path or Path.home() / ".mcp" / "credentials.enc"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get or generate encryption key
        self.password = password or os.getenv("MCP_MASTER_PASSWORD", "")
        if not self.password:
            # Generate from machine ID for automatic but machine-specific encryption
            machine_id = self._get_machine_id()
            self.password = f"mcp-auto-{machine_id}"
        
        self.cipher = self._create_cipher(self.password)
    
    def _get_machine_id(self) -> str:
        """Get a unique machine identifier."""
        # Try various methods to get machine ID
        try:
            # Linux
            if os.path.exists("/etc/machine-id"):
                with open("/etc/machine-id", "r") as f:
                    return f.read().strip()
            # Try hostname + user as fallback
            import socket
            return f"{socket.gethostname()}-{os.getuid() if hasattr(os, 'getuid') else os.environ.get('USERNAME', 'user')}"
        except:
            return "default-machine"
    
    def _create_cipher(self, password: str) -> Fernet:
        """Create cipher from password."""
        # Derive key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'mcp-credential-salt',  # In production, use random salt
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)
    
    async def _load_data(self) -> Dict[str, str]:
        """Load and decrypt credential data."""
        if not self.storage_path.exists():
            return {}
        
        try:
            async with aiofiles.open(self.storage_path, "rb") as f:
                encrypted_data = await f.read()
            
            decrypted_data = self.cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return {}
    
    async def _save_data(self, data: Dict[str, str]) -> None:
        """Encrypt and save credential data."""
        try:
            json_data = json.dumps(data).encode()
            encrypted_data = self.cipher.encrypt(json_data)
            
            async with aiofiles.open(self.storage_path, "wb") as f:
                await f.write(encrypted_data)
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            raise
    
    async def get(self, key: str) -> Optional[str]:
        """Get a credential value."""
        data = await self._load_data()
        return data.get(key)
    
    async def set(self, key: str, value: str) -> None:
        """Set a credential value."""
        data = await self._load_data()
        data[key] = value
        await self._save_data(data)
    
    async def delete(self, key: str) -> None:
        """Delete a credential."""
        data = await self._load_data()
        if key in data:
            del data[key]
            await self._save_data(data)
    
    async def list_keys(self) -> list[str]:
        """List all credential keys."""
        data = await self._load_data()
        return list(data.keys())


class KeyringBackend:
    """System keyring backend (requires keyring package)."""
    
    def __init__(self, service_name: str = "mcp-server"):
        self.service_name = service_name
        try:
            import keyring
            self.keyring = keyring
        except ImportError:
            raise ImportError("keyring package required for KeyringBackend")
    
    async def get(self, key: str) -> Optional[str]:
        """Get a credential value."""
        try:
            return self.keyring.get_password(self.service_name, key)
        except Exception as e:
            logger.error(f"Keyring get error: {e}")
            return None
    
    async def set(self, key: str, value: str) -> None:
        """Set a credential value."""
        try:
            self.keyring.set_password(self.service_name, key, value)
        except Exception as e:
            logger.error(f"Keyring set error: {e}")
            raise
    
    async def delete(self, key: str) -> None:
        """Delete a credential."""
        try:
            self.keyring.delete_password(self.service_name, key)
        except Exception:
            pass  # Ignore if doesn't exist
    
    async def list_keys(self) -> list[str]:
        """List all credential keys (not supported by keyring)."""
        # Most keyring implementations don't support listing
        # We'd need to maintain a separate index
        return []


class CredentialManager:
    """Main credential manager with backend abstraction."""
    
    def __init__(self, backend: CredentialBackend = None):
        """
        Initialize credential manager.
        
        Args:
            backend: Storage backend (defaults to EncryptedFileBackend)
        """
        self.backend = backend or EncryptedFileBackend()
    
    async def get_credential(self, service: str, key: str) -> Optional[str]:
        """
        Get a credential.
        
        Args:
            service: Service name (e.g., "proxmox")
            key: Credential key (e.g., "password")
            
        Returns:
            Credential value or None
        """
        full_key = f"{service}:{key}"
        return await self.backend.get(full_key)
    
    async def set_credential(self, service: str, key: str, value: str) -> None:
        """
        Set a credential.
        
        Args:
            service: Service name (e.g., "proxmox")
            key: Credential key (e.g., "password")
            value: Credential value
        """
        full_key = f"{service}:{key}"
        await self.backend.set(full_key, value)
    
    async def delete_credential(self, service: str, key: str) -> None:
        """Delete a credential."""
        full_key = f"{service}:{key}"
        await self.backend.delete(full_key)
    
    async def get_service_credentials(self, service: str) -> Dict[str, str]:
        """Get all credentials for a service."""
        prefix = f"{service}:"
        all_keys = await self.backend.list_keys()
        
        result = {}
        for key in all_keys:
            if key.startswith(prefix):
                cred_name = key[len(prefix):]
                value = await self.backend.get(key)
                if value:
                    result[cred_name] = value
        
        return result
    
    async def migrate_from_env(self) -> None:
        """Migrate credentials from environment/config to secure storage."""
        from src.utils.config import Config
        
        migrations = [
            ("proxmox", "password", Config.PROXMOX_PASSWORD),
            ("proxmox", "api_token", Config.PROXMOX_API_TOKEN),
            ("ansible", "vault_password", os.getenv("ANSIBLE_VAULT_PASSWORD", "")),
        ]
        
        migrated = 0
        for service, key, value in migrations:
            if value and value != "":
                await self.set_credential(service, key, value)
                migrated += 1
                logger.info(f"Migrated {service}:{key} to secure storage")
        
        return migrated


# Global instance
_credential_manager: Optional[CredentialManager] = None


def get_credential_manager() -> CredentialManager:
    """Get the global credential manager instance."""
    global _credential_manager
    if _credential_manager is None:
        # Check which backend to use
        backend_type = os.getenv("MCP_CREDENTIAL_BACKEND", "encrypted_file")
        
        if backend_type == "keyring":
            try:
                backend = KeyringBackend()
            except ImportError:
                logger.warning("Keyring not available, falling back to encrypted file")
                backend = EncryptedFileBackend()
        else:
            backend = EncryptedFileBackend()
        
        _credential_manager = CredentialManager(backend)
    
    return _credential_manager


# Example usage
async def example():
    """Example of using credential manager."""
    cm = get_credential_manager()
    
    # Store credentials
    await cm.set_credential("proxmox", "password", "secret123")
    await cm.set_credential("proxmox", "api_token", "root@pam!token=abcd")
    
    # Retrieve credentials
    password = await cm.get_credential("proxmox", "password")
    token = await cm.get_credential("proxmox", "api_token")
    
    # Get all proxmox credentials
    proxmox_creds = await cm.get_service_credentials("proxmox")
    
    print(f"Password: {password}")
    print(f"Token: {token}")
    print(f"All Proxmox creds: {proxmox_creds}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example())