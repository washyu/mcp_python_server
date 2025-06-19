"""
MCP SSH Key Manager - Generates and manages SSH keys for homelab automation.
Creates a dedicated SSH key pair for the MCP server to use across all homelab devices.
"""

import os
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class MCPSSHKeyManager:
    """Manages SSH key generation and deployment for MCP homelab automation."""
    
    def __init__(self, ssh_dir: str = None):
        """Initialize SSH key manager."""
        if ssh_dir is None:
            # Use a dedicated .ssh directory in the project
            ssh_dir = Path.home() / ".ssh" / "mcp-homelab"
        
        self.ssh_dir = Path(ssh_dir)
        self.private_key_path = self.ssh_dir / "mcp_homelab_rsa"
        self.public_key_path = self.ssh_dir / "mcp_homelab_rsa.pub"
        self.config_file = self.ssh_dir / "mcp_ssh_config.json"
        
        # Ensure SSH directory exists with proper permissions
        self.ssh_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    
    async def generate_mcp_ssh_key(
        self,
        key_comment: str = None,
        key_type: str = "ed25519",
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a new SSH key pair for MCP homelab automation.
        
        Args:
            key_comment: Comment for the SSH key (default: mcp-homelab-automation)
            key_type: Type of key to generate (ed25519, rsa)
            force_regenerate: Force regeneration even if key exists
            
        Returns:
            Result with key information and paths
        """
        try:
            if key_comment is None:
                key_comment = f"mcp-homelab-automation-{datetime.now().strftime('%Y%m%d')}"
            
            # Check if key already exists
            if self.private_key_path.exists() and not force_regenerate:
                return {
                    "success": False,
                    "error": "SSH key already exists. Use force_regenerate=True to overwrite.",
                    "existing_key": str(self.public_key_path)
                }
            
            # Generate SSH key
            if key_type == "ed25519":
                cmd = [
                    "ssh-keygen",
                    "-t", "ed25519",
                    "-f", str(self.private_key_path),
                    "-C", key_comment,
                    "-N", ""  # No passphrase for automation
                ]
            else:  # RSA
                cmd = [
                    "ssh-keygen",
                    "-t", "rsa",
                    "-b", "4096",
                    "-f", str(self.private_key_path),
                    "-C", key_comment,
                    "-N", ""  # No passphrase for automation
                ]
            
            # Run ssh-keygen
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Failed to generate SSH key: {stderr.decode()}",
                    "command": " ".join(cmd)
                }
            
            # Set proper permissions
            self.private_key_path.chmod(0o600)
            self.public_key_path.chmod(0o644)
            
            # Read the generated public key
            public_key = self.public_key_path.read_text().strip()
            
            # Store key metadata
            key_info = {
                "generated_at": datetime.now().isoformat(),
                "key_type": key_type,
                "comment": key_comment,
                "public_key": public_key,
                "private_key_path": str(self.private_key_path),
                "public_key_path": str(self.public_key_path),
                "fingerprint": await self._get_key_fingerprint()
            }
            
            # Save configuration
            import json
            with open(self.config_file, 'w') as f:
                json.dump(key_info, f, indent=2)
            
            return {
                "success": True,
                "message": "MCP SSH key generated successfully",
                "key_info": key_info
            }
            
        except Exception as e:
            logger.error(f"Failed to generate SSH key: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_mcp_public_key(self) -> Optional[str]:
        """Get the MCP public key if it exists."""
        try:
            if self.public_key_path.exists():
                return self.public_key_path.read_text().strip()
            return None
        except Exception as e:
            logger.error(f"Failed to read public key: {e}")
            return None
    
    async def get_mcp_key_info(self) -> Dict[str, Any]:
        """Get information about the MCP SSH key."""
        try:
            if not self.config_file.exists():
                return {
                    "exists": False,
                    "message": "No MCP SSH key found. Generate one with generate_mcp_ssh_key()"
                }
            
            import json
            with open(self.config_file, 'r') as f:
                key_info = json.load(f)
            
            # Check if files still exist
            private_exists = self.private_key_path.exists()
            public_exists = self.public_key_path.exists()
            
            return {
                "exists": True,
                "private_key_exists": private_exists,
                "public_key_exists": public_exists,
                "key_info": key_info,
                "ready_for_deployment": private_exists and public_exists
            }
            
        except Exception as e:
            logger.error(f"Failed to get key info: {e}")
            return {
                "exists": False,
                "error": str(e)
            }
    
    async def _get_key_fingerprint(self) -> Optional[str]:
        """Get SSH key fingerprint."""
        try:
            cmd = ["ssh-keygen", "-lf", str(self.public_key_path)]
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                # Extract fingerprint from output like "256 SHA256:... comment (ED25519)"
                output = stdout.decode().strip()
                parts = output.split()
                if len(parts) >= 2:
                    return parts[1]  # SHA256:...
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get fingerprint: {e}")
            return None
    
    async def setup_ssh_config_for_ansible(self) -> Dict[str, Any]:
        """Configure SSH settings for Ansible automation."""
        try:
            ssh_config_path = self.ssh_dir / "config"
            
            ssh_config_content = f"""
# MCP Homelab SSH Configuration
Host homelab-*
    User ansible-admin
    IdentityFile {self.private_key_path}
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR
    ConnectTimeout 10
    ServerAliveInterval 60
    ServerAliveCountMax 3

# Default homelab settings
Host 192.168.*
    User ansible-admin
    IdentityFile {self.private_key_path}
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR

Host 10.*
    User ansible-admin
    IdentityFile {self.private_key_path}
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR
"""
            
            ssh_config_path.write_text(ssh_config_content.strip())
            ssh_config_path.chmod(0o600)
            
            # Set SSH_CONFIG environment variable for Ansible
            os.environ['ANSIBLE_SSH_ARGS'] = f'-F {ssh_config_path}'
            
            return {
                "success": True,
                "message": "SSH config created for Ansible automation",
                "config_path": str(ssh_config_path),
                "private_key": str(self.private_key_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to setup SSH config: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def deploy_mcp_key_to_server(
        self,
        host: str,
        initial_auth: Dict[str, Any],
        ansible_user: str = "ansible-admin"
    ) -> Dict[str, Any]:
        """
        Deploy the MCP SSH key to a target server.
        
        Args:
            host: Target hostname or IP
            initial_auth: Initial authentication method
            ansible_user: User to create/configure
            
        Returns:
            Deployment result
        """
        try:
            # Get MCP public key
            public_key = await self.get_mcp_public_key()
            if not public_key:
                return {
                    "success": False,
                    "error": "No MCP SSH key found. Generate one first with generate_mcp_ssh_key()"
                }
            
            # Use the existing deploy_ssh_keys functionality
            from .auth_setup_tools import AuthSetupManager
            
            auth_manager = AuthSetupManager()
            result = await auth_manager.deploy_ssh_keys(
                hosts=host,
                ssh_keys=[public_key],
                username=ansible_user,
                create_user=True,
                sudo_access=True,
                initial_auth=initial_auth
            )
            
            if result.get("success"):
                # Update result to indicate MCP key was used
                result["mcp_key_deployed"] = True
                result["key_source"] = "mcp_generated"
                result["public_key_path"] = str(self.public_key_path)
                result["private_key_path"] = str(self.private_key_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to deploy MCP key: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_mcp_ssh_access(self, host: str, user: str = "ansible-admin") -> Dict[str, Any]:
        """Test SSH access using the MCP key."""
        try:
            if not self.private_key_path.exists():
                return {
                    "success": False,
                    "error": "MCP SSH key not found"
                }
            
            # Test SSH connection
            cmd = [
                "ssh",
                "-i", str(self.private_key_path),
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=10",
                "-o", "BatchMode=yes",
                f"{user}@{host}",
                "echo 'SSH test successful'"
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": f"SSH access to {host} successful",
                    "host": host,
                    "user": user,
                    "output": stdout.decode().strip()
                }
            else:
                return {
                    "success": False,
                    "error": f"SSH connection failed: {stderr.decode()}",
                    "host": host,
                    "user": user
                }
                
        except Exception as e:
            logger.error(f"Failed to test SSH access: {e}")
            return {
                "success": False,
                "error": str(e)
            }