"""
Credential manager for secure storage and retrieval of credentials.
Provides encrypted storage for sensitive authentication data.
"""

import os
import json
import sqlite3
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from cryptography.fernet import Fernet
import base64
import logging

logger = logging.getLogger(__name__)


@dataclass
class CredentialProfile:
    """Represents a credential profile with encrypted data."""
    name: str
    data: Dict[str, Any]
    encryption_version: int = 1
    created_at: str = ""
    updated_at: str = ""


class CredentialManager:
    """Manages encrypted credential storage and retrieval."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize credential manager with database path."""
        if db_path is None:
            db_path = Path.home() / ".mcp" / "credentials.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate or load encryption key
        self._init_encryption()
        
        # Initialize database
        self._init_database()
        
    def _init_encryption(self):
        """Initialize encryption key."""
        key_path = self.db_path.parent / ".key"
        
        if key_path.exists():
            with open(key_path, 'rb') as f:
                self.cipher = Fernet(f.read())
        else:
            # Generate new key
            key = Fernet.generate_key()
            self.cipher = Fernet(key)
            
            # Save key securely (in production, use proper key management)
            with open(key_path, 'wb') as f:
                f.write(key)
            os.chmod(key_path, 0o600)  # Restrict access
            
    def _init_database(self):
        """Initialize SQLite database for credential storage."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create profiles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                name TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                encryption_version INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Create metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        
    def _encrypt_data(self, data: Dict[str, Any]) -> str:
        """Encrypt sensitive data."""
        # Convert to JSON
        json_data = json.dumps(data)
        
        # Encrypt
        encrypted = self.cipher.encrypt(json_data.encode())
        
        # Return base64 encoded for safe storage
        return base64.b64encode(encrypted).decode()
        
    def _decrypt_data(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt sensitive data."""
        try:
            # Decode from base64
            encrypted = base64.b64decode(encrypted_data.encode())
            
            # Decrypt
            decrypted = self.cipher.decrypt(encrypted)
            
            # Parse JSON
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            raise ValueError("Failed to decrypt credentials")
            
    async def store_credentials(self, profile_name: str, credentials: Dict[str, Any]) -> bool:
        """Store credentials securely."""
        try:
            # Encrypt sensitive fields
            encrypted_creds = credentials.copy()
            sensitive_fields = ['password', 'api_token', 'secret', 'key']
            
            for field in sensitive_fields:
                if field in encrypted_creds and encrypted_creds[field]:
                    encrypted_creds[field] = self._encrypt_data({field: encrypted_creds[field]})
                    
            # Create profile
            profile = CredentialProfile(
                name=profile_name,
                data=encrypted_creds,
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat()
            )
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO profiles (name, data, encryption_version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                profile.name,
                json.dumps(profile.data),
                profile.encryption_version,
                profile.created_at,
                profile.updated_at
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Stored credentials for profile: {profile_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store credentials: {e}")
            return False
            
    async def get_credentials(self, profile_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt credentials."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT data FROM profiles WHERE name = ?
            """, (profile_name,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
                
            # Parse stored data
            stored_data = json.loads(row[0])
            
            # Decrypt sensitive fields
            decrypted_data = stored_data.copy()
            sensitive_fields = ['password', 'api_token', 'secret', 'key']
            
            for field in sensitive_fields:
                if field in decrypted_data and isinstance(decrypted_data[field], str):
                    try:
                        # Decrypt the field
                        decrypted_value = self._decrypt_data(decrypted_data[field])
                        decrypted_data[field] = decrypted_value.get(field, "")
                    except:
                        # Field might not be encrypted
                        pass
                        
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Failed to retrieve credentials: {e}")
            return None
            
    async def list_profiles(self) -> List[str]:
        """List all credential profiles."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM profiles")
            profiles = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            return profiles
            
        except Exception as e:
            logger.error(f"Failed to list profiles: {e}")
            return []
            
    async def delete_profile(self, profile_name: str) -> bool:
        """Delete a credential profile."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM profiles WHERE name = ?", (profile_name,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Deleted profile: {profile_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete profile: {e}")
            return False
            
    async def migrate_from_env(self, env_path: Path = Path(".env")) -> bool:
        """Migrate credentials from .env file to secure storage."""
        try:
            if not env_path.exists():
                return False
                
            # Read .env file
            env_vars = {}
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
                        
            # Extract Proxmox credentials
            if 'PROXMOX_HOST' in env_vars:
                proxmox_creds = {
                    'host': env_vars.get('PROXMOX_HOST', ''),
                    'username': env_vars.get('PROXMOX_USER', ''),
                    'password': env_vars.get('PROXMOX_PASSWORD', ''),
                    'api_token': env_vars.get('PROXMOX_API_TOKEN', ''),
                    'verify_ssl': env_vars.get('PROXMOX_VERIFY_SSL', 'true').lower() == 'true'
                }
                
                await self.store_credentials('proxmox', proxmox_creds)
                
            # Extract Ansible credentials
            if 'ANSIBLE_HOST' in env_vars:
                ansible_creds = {
                    'host': env_vars.get('ANSIBLE_HOST', ''),
                    'username': env_vars.get('ANSIBLE_USER', ''),
                    'password': env_vars.get('ANSIBLE_PASSWORD', ''),
                    'ssh_key_path': env_vars.get('ANSIBLE_SSH_KEY', '')
                }
                
                await self.store_credentials('ansible', ansible_creds)
                
            logger.info("Successfully migrated credentials from .env")
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate from .env: {e}")
            return False


# Singleton instance
_credential_manager = None


def get_credential_manager() -> CredentialManager:
    """Get singleton instance of credential manager."""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager


async def get_proxmox_credentials() -> Optional[Dict[str, Any]]:
    """Helper function to get Proxmox credentials."""
    manager = get_credential_manager()
    return await manager.get_credentials('proxmox')


async def get_ansible_credentials() -> Optional[Dict[str, Any]]:
    """Helper function to get Ansible credentials."""
    manager = get_credential_manager()
    return await manager.get_credentials('ansible')