"""
Configuration management for Ansible MCP Server.
Loads settings from environment variables and .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

class Config:
    """Configuration settings for the MCP server."""
    
    # Ollama Configuration
    OLLAMA_HOST: str = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    OLLAMA_MODEL: str = os.getenv('OLLAMA_MODEL', 'deepseek-r1:8b')  # Great for reasoning tasks!
    
    # Proxmox Configuration
    PROXMOX_HOST: str = os.getenv('PROXMOX_HOST', '192.168.10.200')
    PROXMOX_USER: str = os.getenv('PROXMOX_USER', 'root@pam')
    PROXMOX_PASSWORD: str = os.getenv('PROXMOX_PASSWORD', '')
    PROXMOX_API_TOKEN: str = os.getenv('PROXMOX_API_TOKEN', '')  # Format: user@realm!tokenid=uuid
    PROXMOX_VERIFY_SSL: bool = os.getenv('PROXMOX_VERIFY_SSL', 'false').lower() == 'true'
    
    # Ansible Configuration
    ANSIBLE_HOST_KEY_CHECKING: bool = os.getenv('ANSIBLE_HOST_KEY_CHECKING', 'false').lower() == 'true'
    ANSIBLE_INVENTORY_PATH: str = os.getenv('ANSIBLE_INVENTORY_PATH', './inventory/hosts.yml')
    
    # MCP Server Configuration
    MCP_SERVER_NAME: str = os.getenv('MCP_SERVER_NAME', 'ansible-mcp-server')
    MCP_SERVER_VERSION: str = os.getenv('MCP_SERVER_VERSION', '0.1.0')
    
    # Development Settings
    DEBUG: bool = os.getenv('DEBUG', 'false').lower() == 'true'
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    # Inventory Management
    INVENTORY_STALENESS_HOURS: int = int(os.getenv('INVENTORY_STALENESS_HOURS', '10'))
    INVENTORY_PATH: Path = Path(os.getenv('INVENTORY_PATH', './inventory'))
    
    # Template VM Configuration
    TEMPLATE_VM_ID: int = int(os.getenv('TEMPLATE_VM_ID', '9000'))
    TEMPLATE_VM_NAME: str = os.getenv('TEMPLATE_VM_NAME', 'ubuntu-cloud-template')
    DEFAULT_VM_USER: str = os.getenv('DEFAULT_VM_USER', 'ansible-admin')
    
    @classmethod
    def get_ollama_client_params(cls) -> dict:
        """Get parameters for Ollama client initialization."""
        return {
            'host': cls.OLLAMA_HOST
        }
    
    @classmethod
    def validate(cls) -> None:
        """Validate critical configuration settings."""
        errors = []
        
        # Check if Proxmox password is set when needed
        if not cls.PROXMOX_PASSWORD and cls.PROXMOX_HOST:
            errors.append("PROXMOX_PASSWORD not set - required for Proxmox operations")
        
        # Ensure inventory path exists
        if not cls.INVENTORY_PATH.exists():
            cls.INVENTORY_PATH.mkdir(parents=True, exist_ok=True)
        
        if errors:
            import sys
            print("Configuration warnings:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
    
    @classmethod
    def display(cls) -> None:
        """Display current configuration (hiding sensitive values)."""
        print("Current Configuration:")
        print(f"  Ollama Host: {cls.OLLAMA_HOST}")
        print(f"  Ollama Model: {cls.OLLAMA_MODEL}")
        print(f"  Proxmox Host: {cls.PROXMOX_HOST}")
        print(f"  Proxmox User: {cls.PROXMOX_USER}")
        print(f"  Proxmox Password: {'*' * len(cls.PROXMOX_PASSWORD) if cls.PROXMOX_PASSWORD else 'NOT SET'}")
        print(f"  Debug Mode: {cls.DEBUG}")
        print(f"  Log Level: {cls.LOG_LEVEL}")


# Validate configuration on import
Config.validate()