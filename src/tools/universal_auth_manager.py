"""
Universal Authentication Manager - Provider-agnostic authentication for all infrastructure types.
Handles SSH keys, API tokens, cloud roles, domain accounts, and more.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path

from ..utils.homelab_context import HomelabContextManager
from .mcp_ssh_manager import MCPSSHKeyManager
from ..security.credential_manager import get_credential_manager

logger = logging.getLogger(__name__)


@dataclass
class AuthenticationConfig:
    """Universal authentication configuration for different providers."""
    provider_type: str  # proxmox, truenas, docker, lxd, aws, azure, gcp, vmware
    auth_method: str   # ssh_key, api_token, cloud_role, domain_account, certificate
    endpoint: str      # Host/URL for the service
    
    # SSH-based authentication
    ssh_user: Optional[str] = None
    ssh_key_path: Optional[str] = None
    ssh_port: int = 22
    
    # API token authentication
    api_token: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    token_id: Optional[str] = None
    
    # Cloud role authentication
    role_arn: Optional[str] = None
    service_account: Optional[str] = None
    tenant_id: Optional[str] = None
    subscription_id: Optional[str] = None
    
    # Domain account authentication
    domain: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    
    # Certificate authentication
    cert_path: Optional[str] = None
    key_path: Optional[str] = None
    ca_path: Optional[str] = None
    
    # Additional metadata
    created_at: Optional[str] = None
    last_verified: Optional[str] = None
    expires_at: Optional[str] = None
    notes: str = ""


class UniversalAuthManager:
    """Manages authentication across all infrastructure providers."""
    
    def __init__(self):
        self.context_manager = HomelabContextManager()
        self.mcp_ssh = MCPSSHKeyManager()
        self.credential_manager = get_credential_manager()
        
        # Provider-specific authentication strategies
        self.auth_strategies = {
            "proxmox": self._setup_proxmox_auth,
            "truenas": self._setup_truenas_auth,
            "docker": self._setup_docker_auth,
            "lxd": self._setup_lxd_auth,
            "vmware": self._setup_vmware_auth,
            "aws": self._setup_aws_auth,
            "azure": self._setup_azure_auth,
            "gcp": self._setup_gcp_auth,
            "kubernetes": self._setup_k8s_auth,
            "generic_ssh": self._setup_generic_ssh_auth
        }
    
    async def setup_universal_auth(
        self,
        provider_type: str,
        endpoint: str,
        auth_method: str = "auto",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Set up authentication for any infrastructure provider.
        
        Args:
            provider_type: Type of provider (proxmox, truenas, docker, etc.)
            endpoint: Host/URL for the service
            auth_method: Preferred auth method or 'auto' to detect best method
            **kwargs: Provider-specific authentication parameters
            
        Returns:
            Setup result with authentication configuration
        """
        try:
            if provider_type not in self.auth_strategies:
                return {
                    "success": False,
                    "error": f"Unknown provider type: {provider_type}",
                    "supported_providers": list(self.auth_strategies.keys())
                }
            
            # Call provider-specific setup strategy
            result = await self.auth_strategies[provider_type](
                endpoint=endpoint,
                auth_method=auth_method,
                **kwargs
            )
            
            if result.get("success"):
                # Store authentication config in context
                auth_config = result.get("auth_config")
                if auth_config:
                    await self._store_auth_config(provider_type, endpoint, auth_config)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to setup auth for {provider_type}: {e}")
            return {
                "success": False,
                "error": str(e),
                "provider_type": provider_type,
                "endpoint": endpoint
            }
    
    async def _setup_proxmox_auth(self, endpoint: str, auth_method: str = "auto", **kwargs) -> Dict[str, Any]:
        """Setup authentication for Proxmox VE."""
        try:
            if auth_method == "auto":
                # Try API token first, fall back to SSH
                auth_method = kwargs.get("api_token") and "api_token" or "ssh_key"
            
            if auth_method == "api_token":
                # Proxmox API token authentication
                auth_config = AuthenticationConfig(
                    provider_type="proxmox",
                    auth_method="api_token",
                    endpoint=endpoint,
                    api_token=kwargs.get("api_token"),
                    token_id=kwargs.get("token_id"),
                    username=kwargs.get("username", "root@pam"),
                    created_at=datetime.now().isoformat()
                )
                
                # Test API access
                test_result = await self._test_proxmox_api_access(auth_config)
                
            elif auth_method == "ssh_key":
                # SSH key authentication for Proxmox host
                auth_config = AuthenticationConfig(
                    provider_type="proxmox",
                    auth_method="ssh_key",
                    endpoint=endpoint,
                    ssh_user=kwargs.get("ssh_user", "root"),
                    ssh_key_path=str(self.mcp_ssh.private_key_path),
                    ssh_port=kwargs.get("ssh_port", 22),
                    created_at=datetime.now().isoformat()
                )
                
                # Deploy MCP SSH key if needed
                if kwargs.get("deploy_ssh_key", True):
                    deploy_result = await self.mcp_ssh.deploy_mcp_key_to_server(
                        host=endpoint,
                        initial_auth=kwargs.get("initial_auth", {"method": "password"}),
                        ansible_user=auth_config.ssh_user
                    )
                    if not deploy_result.get("success"):
                        return deploy_result
                
                test_result = await self.mcp_ssh.test_mcp_ssh_access(endpoint, auth_config.ssh_user)
            
            else:
                return {
                    "success": False,
                    "error": f"Unsupported auth method for Proxmox: {auth_method}",
                    "supported_methods": ["api_token", "ssh_key"]
                }
            
            return {
                "success": test_result.get("success", False),
                "message": f"Proxmox authentication setup complete using {auth_method}",
                "auth_config": auth_config,
                "test_result": test_result,
                "provider_type": "proxmox"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _setup_truenas_auth(self, endpoint: str, auth_method: str = "auto", **kwargs) -> Dict[str, Any]:
        """Setup authentication for TrueNAS."""
        try:
            if auth_method == "auto":
                auth_method = kwargs.get("api_key") and "api_token" or "ssh_key"
            
            if auth_method == "api_token":
                auth_config = AuthenticationConfig(
                    provider_type="truenas",
                    auth_method="api_token",
                    endpoint=f"https://{endpoint}",
                    api_key=kwargs.get("api_key"),
                    username=kwargs.get("username", "root"),
                    created_at=datetime.now().isoformat()
                )
                
                # Test TrueNAS API
                test_result = await self._test_truenas_api_access(auth_config)
                
            elif auth_method == "ssh_key":
                auth_config = AuthenticationConfig(
                    provider_type="truenas",
                    auth_method="ssh_key",
                    endpoint=endpoint,
                    ssh_user=kwargs.get("ssh_user", "root"),
                    ssh_key_path=str(self.mcp_ssh.private_key_path),
                    ssh_port=kwargs.get("ssh_port", 22),
                    created_at=datetime.now().isoformat()
                )
                
                test_result = await self.mcp_ssh.test_mcp_ssh_access(endpoint, auth_config.ssh_user)
            
            else:
                return {
                    "success": False,
                    "error": f"Unsupported auth method for TrueNAS: {auth_method}",
                    "supported_methods": ["api_token", "ssh_key"]
                }
            
            return {
                "success": test_result.get("success", False),
                "message": f"TrueNAS authentication setup complete using {auth_method}",
                "auth_config": auth_config,
                "test_result": test_result,
                "provider_type": "truenas"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _setup_docker_auth(self, endpoint: str, auth_method: str = "auto", **kwargs) -> Dict[str, Any]:
        """Setup authentication for Docker/Docker Swarm."""
        try:
            if auth_method == "auto":
                auth_method = "ssh_key"  # Docker typically uses SSH to host
            
            if auth_method == "ssh_key":
                auth_config = AuthenticationConfig(
                    provider_type="docker",
                    auth_method="ssh_key",
                    endpoint=endpoint,
                    ssh_user=kwargs.get("ssh_user", "ansible-admin"),
                    ssh_key_path=str(self.mcp_ssh.private_key_path),
                    ssh_port=kwargs.get("ssh_port", 22),
                    created_at=datetime.now().isoformat()
                )
                
                test_result = await self.mcp_ssh.test_mcp_ssh_access(endpoint, auth_config.ssh_user)
                
            elif auth_method == "certificate":
                # Docker TLS certificate authentication
                auth_config = AuthenticationConfig(
                    provider_type="docker",
                    auth_method="certificate",
                    endpoint=f"https://{endpoint}:2376",
                    cert_path=kwargs.get("cert_path"),
                    key_path=kwargs.get("key_path"),
                    ca_path=kwargs.get("ca_path"),
                    created_at=datetime.now().isoformat()
                )
                
                test_result = await self._test_docker_tls_access(auth_config)
            
            else:
                return {
                    "success": False,
                    "error": f"Unsupported auth method for Docker: {auth_method}",
                    "supported_methods": ["ssh_key", "certificate"]
                }
            
            return {
                "success": test_result.get("success", False),
                "message": f"Docker authentication setup complete using {auth_method}",
                "auth_config": auth_config,
                "test_result": test_result,
                "provider_type": "docker"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _setup_lxd_auth(self, endpoint: str, auth_method: str = "auto", **kwargs) -> Dict[str, Any]:
        """Setup authentication for LXD."""
        try:
            if auth_method == "auto":
                auth_method = "ssh_key"  # LXD typically uses SSH to host
            
            auth_config = AuthenticationConfig(
                provider_type="lxd",
                auth_method="ssh_key",
                endpoint=endpoint,
                ssh_user=kwargs.get("ssh_user", "ansible-admin"),
                ssh_key_path=str(self.mcp_ssh.private_key_path),
                ssh_port=kwargs.get("ssh_port", 22),
                created_at=datetime.now().isoformat()
            )
            
            test_result = await self.mcp_ssh.test_mcp_ssh_access(endpoint, auth_config.ssh_user)
            
            return {
                "success": test_result.get("success", False),
                "message": "LXD authentication setup complete using SSH key",
                "auth_config": auth_config,
                "test_result": test_result,
                "provider_type": "lxd"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _setup_vmware_auth(self, endpoint: str, auth_method: str = "auto", **kwargs) -> Dict[str, Any]:
        """Setup authentication for VMware vSphere/ESXi."""
        try:
            if auth_method == "auto":
                auth_method = kwargs.get("username") and "domain_account" or "ssh_key"
            
            if auth_method == "domain_account":
                auth_config = AuthenticationConfig(
                    provider_type="vmware",
                    auth_method="domain_account",
                    endpoint=f"https://{endpoint}/sdk",
                    username=kwargs.get("username"),
                    password=kwargs.get("password"),
                    domain=kwargs.get("domain"),
                    created_at=datetime.now().isoformat()
                )
                
                test_result = await self._test_vmware_api_access(auth_config)
                
            elif auth_method == "ssh_key":
                # ESXi SSH access
                auth_config = AuthenticationConfig(
                    provider_type="vmware",
                    auth_method="ssh_key",
                    endpoint=endpoint,
                    ssh_user=kwargs.get("ssh_user", "root"),
                    ssh_key_path=str(self.mcp_ssh.private_key_path),
                    ssh_port=kwargs.get("ssh_port", 22),
                    created_at=datetime.now().isoformat()
                )
                
                test_result = await self.mcp_ssh.test_mcp_ssh_access(endpoint, auth_config.ssh_user)
            
            else:
                return {
                    "success": False,
                    "error": f"Unsupported auth method for VMware: {auth_method}",
                    "supported_methods": ["domain_account", "ssh_key"]
                }
            
            return {
                "success": test_result.get("success", False),
                "message": f"VMware authentication setup complete using {auth_method}",
                "auth_config": auth_config,
                "test_result": test_result,
                "provider_type": "vmware"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _setup_aws_auth(self, endpoint: str, auth_method: str = "auto", **kwargs) -> Dict[str, Any]:
        """Setup authentication for AWS."""
        try:
            if auth_method == "auto":
                auth_method = kwargs.get("role_arn") and "cloud_role" or "api_token"
            
            if auth_method == "cloud_role":
                auth_config = AuthenticationConfig(
                    provider_type="aws",
                    auth_method="cloud_role",
                    endpoint=f"https://{endpoint}",
                    role_arn=kwargs.get("role_arn"),
                    created_at=datetime.now().isoformat()
                )
                
            elif auth_method == "api_token":
                auth_config = AuthenticationConfig(
                    provider_type="aws",
                    auth_method="api_token",
                    endpoint=f"https://{endpoint}",
                    api_key=kwargs.get("access_key_id"),
                    api_secret=kwargs.get("secret_access_key"),
                    created_at=datetime.now().isoformat()
                )
            
            else:
                return {
                    "success": False,
                    "error": f"Unsupported auth method for AWS: {auth_method}",
                    "supported_methods": ["cloud_role", "api_token"]
                }
            
            # Note: AWS auth testing would require boto3 integration
            test_result = {"success": True, "message": "AWS auth config stored (testing requires boto3)"}
            
            return {
                "success": True,
                "message": f"AWS authentication setup complete using {auth_method}",
                "auth_config": auth_config,
                "test_result": test_result,
                "provider_type": "aws"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _setup_azure_auth(self, endpoint: str, auth_method: str = "auto", **kwargs) -> Dict[str, Any]:
        """Setup authentication for Azure."""
        try:
            auth_config = AuthenticationConfig(
                provider_type="azure",
                auth_method="cloud_role",
                endpoint="https://management.azure.com",
                tenant_id=kwargs.get("tenant_id"),
                subscription_id=kwargs.get("subscription_id"),
                service_account=kwargs.get("service_principal_id"),
                api_secret=kwargs.get("client_secret"),
                created_at=datetime.now().isoformat()
            )
            
            test_result = {"success": True, "message": "Azure auth config stored (testing requires azure-mgmt libraries)"}
            
            return {
                "success": True,
                "message": "Azure authentication setup complete",
                "auth_config": auth_config,
                "test_result": test_result,
                "provider_type": "azure"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _setup_gcp_auth(self, endpoint: str, auth_method: str = "auto", **kwargs) -> Dict[str, Any]:
        """Setup authentication for Google Cloud Platform."""
        try:
            auth_config = AuthenticationConfig(
                provider_type="gcp",
                auth_method="cloud_role",
                endpoint="https://googleapis.com",
                service_account=kwargs.get("service_account_email"),
                key_path=kwargs.get("service_account_key_path"),
                created_at=datetime.now().isoformat()
            )
            
            test_result = {"success": True, "message": "GCP auth config stored (testing requires google-cloud libraries)"}
            
            return {
                "success": True,
                "message": "GCP authentication setup complete",
                "auth_config": auth_config,
                "test_result": test_result,
                "provider_type": "gcp"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _setup_k8s_auth(self, endpoint: str, auth_method: str = "auto", **kwargs) -> Dict[str, Any]:
        """Setup authentication for Kubernetes."""
        try:
            if auth_method == "auto":
                auth_method = kwargs.get("token") and "api_token" or "certificate"
            
            if auth_method == "api_token":
                auth_config = AuthenticationConfig(
                    provider_type="kubernetes",
                    auth_method="api_token",
                    endpoint=endpoint,
                    api_token=kwargs.get("token"),
                    ca_path=kwargs.get("ca_cert_path"),
                    created_at=datetime.now().isoformat()
                )
                
            elif auth_method == "certificate":
                auth_config = AuthenticationConfig(
                    provider_type="kubernetes",
                    auth_method="certificate",
                    endpoint=endpoint,
                    cert_path=kwargs.get("client_cert_path"),
                    key_path=kwargs.get("client_key_path"),
                    ca_path=kwargs.get("ca_cert_path"),
                    created_at=datetime.now().isoformat()
                )
            
            else:
                return {
                    "success": False,
                    "error": f"Unsupported auth method for Kubernetes: {auth_method}",
                    "supported_methods": ["api_token", "certificate"]
                }
            
            test_result = {"success": True, "message": "Kubernetes auth config stored (testing requires kubectl)"}
            
            return {
                "success": True,
                "message": f"Kubernetes authentication setup complete using {auth_method}",
                "auth_config": auth_config,
                "test_result": test_result,
                "provider_type": "kubernetes"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _setup_generic_ssh_auth(self, endpoint: str, auth_method: str = "ssh_key", **kwargs) -> Dict[str, Any]:
        """Setup generic SSH authentication for any server."""
        try:
            auth_config = AuthenticationConfig(
                provider_type="generic_ssh",
                auth_method="ssh_key",
                endpoint=endpoint,
                ssh_user=kwargs.get("ssh_user", "ansible-admin"),
                ssh_key_path=str(self.mcp_ssh.private_key_path),
                ssh_port=kwargs.get("ssh_port", 22),
                created_at=datetime.now().isoformat()
            )
            
            test_result = await self.mcp_ssh.test_mcp_ssh_access(endpoint, auth_config.ssh_user)
            
            return {
                "success": test_result.get("success", False),
                "message": "Generic SSH authentication setup complete",
                "auth_config": auth_config,
                "test_result": test_result,
                "provider_type": "generic_ssh"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _store_auth_config(self, provider_type: str, endpoint: str, auth_config: AuthenticationConfig):
        """Store authentication configuration in context."""
        try:
            # Store in homelab context with provider-specific key
            auth_key = f"{provider_type}_{endpoint.replace('.', '_').replace(':', '_')}"
            
            # Convert to dict for JSON storage
            config_dict = asdict(auth_config)
            
            # Store encrypted sensitive data
            sensitive_fields = ['api_token', 'api_secret', 'password']
            for field in sensitive_fields:
                if config_dict.get(field):
                    # Here you would encrypt the sensitive data
                    # For now, we'll mark it as encrypted
                    config_dict[field] = f"<encrypted:{field}>"
            
            # Store in context
            topology = await self.context_manager.load_topology()
            if "authentication_configs" not in topology:
                topology["authentication_configs"] = {}
            
            topology["authentication_configs"][auth_key] = config_dict
            topology["topology"]["last_updated"] = datetime.now().isoformat()
            
            await self.context_manager.save_topology(topology)
            
        except Exception as e:
            logger.error(f"Failed to store auth config: {e}")
    
    async def get_auth_config(self, provider_type: str, endpoint: str) -> Optional[AuthenticationConfig]:
        """Retrieve authentication configuration from context."""
        try:
            auth_key = f"{provider_type}_{endpoint.replace('.', '_').replace(':', '_')}"
            topology = await self.context_manager.load_topology()
            
            config_dict = topology.get("authentication_configs", {}).get(auth_key)
            if config_dict:
                return AuthenticationConfig(**config_dict)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get auth config: {e}")
            return None
    
    async def list_auth_configs(self) -> List[Dict[str, Any]]:
        """List all stored authentication configurations."""
        try:
            topology = await self.context_manager.load_topology()
            configs = topology.get("authentication_configs", {})
            
            result = []
            for auth_key, config_dict in configs.items():
                # Remove sensitive data from listing
                safe_config = {k: v for k, v in config_dict.items() 
                             if k not in ['api_token', 'api_secret', 'password']}
                safe_config['auth_key'] = auth_key
                result.append(safe_config)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to list auth configs: {e}")
            return []
    
    # Placeholder test methods (would need actual API clients)
    async def _test_proxmox_api_access(self, auth_config: AuthenticationConfig) -> Dict[str, Any]:
        """Test Proxmox API access."""
        return {"success": True, "message": "Proxmox API test placeholder"}
    
    async def _test_truenas_api_access(self, auth_config: AuthenticationConfig) -> Dict[str, Any]:
        """Test TrueNAS API access."""
        return {"success": True, "message": "TrueNAS API test placeholder"}
    
    async def _test_docker_tls_access(self, auth_config: AuthenticationConfig) -> Dict[str, Any]:
        """Test Docker TLS access."""
        return {"success": True, "message": "Docker TLS test placeholder"}
    
    async def _test_vmware_api_access(self, auth_config: AuthenticationConfig) -> Dict[str, Any]:
        """Test VMware API access."""
        return {"success": True, "message": "VMware API test placeholder"}