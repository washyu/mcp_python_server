"""
Secure configuration that integrates with credential manager.
Provides backward compatibility with existing Config class.
"""

import os
import asyncio
from typing import Optional, Dict, Any
from src.utils.config import Config as BaseConfig
from src.utils.credential_manager import get_credential_manager
import logging

logger = logging.getLogger(__name__)


class SecureConfig:
    """Configuration with secure credential storage."""
    
    def __init__(self):
        self.cm = get_credential_manager()
        self._cache: Dict[str, Any] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize and load secure credentials."""
        if self._initialized:
            return
        
        # Check if we should migrate from env
        if os.getenv("MCP_MIGRATE_CREDENTIALS", "").lower() == "true":
            logger.info("Migrating credentials to secure storage...")
            migrated = await self.cm.migrate_from_env()
            logger.info(f"Migrated {migrated} credentials")
        
        # Load credentials into cache
        await self._load_credentials()
        self._initialized = True
    
    async def _load_credentials(self):
        """Load credentials from secure storage."""
        # Load Proxmox credentials
        proxmox_creds = await self.cm.get_service_credentials("proxmox")
        self._cache.update({
            "PROXMOX_PASSWORD": proxmox_creds.get("password", ""),
            "PROXMOX_API_TOKEN": proxmox_creds.get("api_token", "")
        })
        
        # Load Ansible credentials
        ansible_creds = await self.cm.get_service_credentials("ansible")
        self._cache.update({
            "ANSIBLE_VAULT_PASSWORD": ansible_creds.get("vault_password", "")
        })
    
    def __getattr__(self, name: str) -> Any:
        """Get config value, checking secure storage for credentials."""
        # Check if it's a credential field
        if name in ["PROXMOX_PASSWORD", "PROXMOX_API_TOKEN", "ANSIBLE_VAULT_PASSWORD"]:
            # Return from cache (loaded during initialization)
            value = self._cache.get(name)
            if value:
                return value
        
        # Fall back to base config
        return getattr(BaseConfig, name)
    
    @classmethod
    def get_ollama_client_params(cls) -> dict:
        """Get Ollama client parameters."""
        return BaseConfig.get_ollama_client_params()
    
    async def update_credential(self, service: str, key: str, value: str):
        """Update a credential in secure storage."""
        await self.cm.set_credential(service, key, value)
        
        # Update cache
        cache_key = f"{service.upper()}_{key.upper()}"
        self._cache[cache_key] = value
    
    async def get_proxmox_config(self) -> Dict[str, Any]:
        """Get complete Proxmox configuration."""
        return {
            "host": self.PROXMOX_HOST,
            "username": self.PROXMOX_USER,
            "password": self.PROXMOX_PASSWORD,
            "api_token": self.PROXMOX_API_TOKEN,
            "verify_ssl": self.PROXMOX_VERIFY_SSL
        }


# Global secure config instance
_secure_config: Optional[SecureConfig] = None


def get_secure_config() -> SecureConfig:
    """Get the global secure config instance."""
    global _secure_config
    if _secure_config is None:
        _secure_config = SecureConfig()
    return _secure_config


# Compatibility wrapper
class ConfigProxy:
    """Proxy that provides sync access to secure config."""
    
    def __init__(self):
        self._secure_config = get_secure_config()
        self._loop = None
        
        # Ensure initialized
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop, create one for sync initialization
            self._loop = asyncio.new_event_loop()
            self._loop.run_until_complete(self._secure_config.initialize())
    
    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to secure config."""
        return getattr(self._secure_config, name)


# Usage example for discovery tools
async def get_proxmox_client_config():
    """Get Proxmox client configuration from secure storage."""
    config = get_secure_config()
    await config.initialize()
    
    # Check for API token first (preferred)
    if config.PROXMOX_API_TOKEN:
        return {
            "host": config.PROXMOX_HOST,
            "api_token": config.PROXMOX_API_TOKEN,
            "verify_ssl": config.PROXMOX_VERIFY_SSL
        }
    else:
        return {
            "host": config.PROXMOX_HOST,
            "username": config.PROXMOX_USER,
            "password": config.PROXMOX_PASSWORD,
            "verify_ssl": config.PROXMOX_VERIFY_SSL
        }