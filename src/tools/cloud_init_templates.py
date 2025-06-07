"""
Cloud-Init templates and configurations for VM creation.
"""

import secrets
import string
import yaml
from typing import Dict, List, Optional, Any
from pathlib import Path


class CloudInitTemplates:
    """Cloud-init configuration templates for different VM types."""
    
    @staticmethod
    def generate_secure_password(length: int = 20) -> str:
        """Generate a secure random password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def get_mcp_ssh_key() -> Optional[str]:
        """Get MCP server SSH public key if available."""
        ssh_key_paths = [
            Path.home() / ".ssh" / "id_rsa.pub",
            Path.home() / ".ssh" / "id_ed25519.pub", 
            Path("/root/.ssh/id_rsa.pub"),
            Path("/home/ansible/.ssh/id_rsa.pub")
        ]
        
        for key_path in ssh_key_paths:
            try:
                if key_path.exists():
                    return key_path.read_text().strip()
            except Exception:
                continue
        
        return None
    
    @classmethod
    def base_vm_config(
        cls,
        hostname: str,
        username: str = "ansible-admin",
        ssh_keys: List[str] = None,
        additional_packages: List[str] = None,
        additional_commands: List[str] = None
    ) -> Dict[str, Any]:
        """
        Base cloud-init configuration for all VMs.
        
        Includes:
        - qemu-guest-agent (essential for Proxmox)
        - ansible-admin user with sudo access
        - SSH key configuration
        - Security hardening
        - Basic utilities
        """
        
        # Generate secure password
        password = cls.generate_secure_password()
        
        # Base packages for all VMs
        base_packages = [
            # Essential for Proxmox integration
            "qemu-guest-agent",
            
            # SSH and remote access
            "openssh-server",
            
            # Ansible requirements
            "python3",
            "python3-pip",
            "python3-setuptools",
            
            # Basic utilities
            "curl",
            "wget", 
            "nano",
            "vim",
            "htop",
            "tree",
            "unzip",
            "git",
            
            # System monitoring
            "netstat-nat",
            "iotop",
            "lsof",
            
            # Security
            "fail2ban",
            "ufw"
        ]
        
        # Add additional packages
        if additional_packages:
            base_packages.extend(additional_packages)
        
        # Collect SSH keys
        all_ssh_keys = ssh_keys or []
        
        # Add MCP server SSH key if available
        mcp_key = cls.get_mcp_ssh_key()
        if mcp_key:
            all_ssh_keys.append(mcp_key)
        
        # Base commands to run
        base_commands = [
            # System update
            "apt-get update",
            "apt-get upgrade -y",
            
            # Enable and start qemu-guest-agent (CRITICAL for Proxmox)
            "systemctl enable qemu-guest-agent",
            "systemctl start qemu-guest-agent",
            
            # Configure ansible-admin user
            f"mkdir -p /home/{username}/.ssh",
            f"chmod 700 /home/{username}/.ssh", 
            f"chown {username}:{username} /home/{username}/.ssh",
            
            # Enable passwordless sudo for ansible-admin
            f"echo '{username} ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/{username}",
            f"chmod 440 /etc/sudoers.d/{username}",
            
            # Basic security hardening
            "systemctl enable fail2ban",
            "systemctl start fail2ban",
            "ufw --force enable",
            "ufw default deny incoming",
            "ufw default allow outgoing", 
            "ufw allow ssh",
            
            # Set timezone
            "timedatectl set-timezone UTC",
            
            # Clean up
            "apt-get autoremove -y",
            "apt-get autoclean"
        ]
        
        # Add additional commands
        if additional_commands:
            base_commands.extend(additional_commands)
        
        return {
            "users": [
                {
                    "name": username,
                    "groups": ["sudo", "adm", "systemd-journal"],
                    "shell": "/bin/bash",
                    "sudo": "ALL=(ALL) NOPASSWD:ALL",
                    "lock_passwd": False,
                    "passwd": password,
                    "ssh_authorized_keys": all_ssh_keys,
                    "gecos": f"Ansible Admin User for {hostname}"
                }
            ],
            "packages": base_packages,
            "runcmd": base_commands,
            
            # SSH configuration
            "ssh_pwauth": True,
            "disable_root": False,  # Keep root enabled for emergency access
            "ssh_deletekeys": True,  # Regenerate SSH host keys
            
            # System configuration
            "package_update": True,
            "package_upgrade": True,
            "timezone": "UTC",
            "locale": "en_US.UTF-8",
            "manage_etc_hosts": True,
            "preserve_hostname": False,
            "hostname": hostname,
            "fqdn": f"{hostname}.local",
            
            # Cloud-init behavior
            "cloud_final_modules": [
                "package-update-upgrade-install",
                "scripts-vendor", 
                "scripts-per-once",
                "scripts-per-boot",
                "scripts-per-instance",
                "scripts-user",
                "ssh-authkey-fingerprints",
                "keys-to-console",
                "phone-home",
                "final-message"
            ],
            
            # Store generated password (will be implemented in credential manager)
            "_mcp_generated_password": password
        }
    
    @classmethod
    def development_vm_config(cls, hostname: str, **kwargs) -> Dict[str, Any]:
        """Cloud-init config for development VMs."""
        dev_packages = [
            "build-essential",
            "nodejs",
            "npm", 
            "docker.io",
            "docker-compose",
            "code-server"  # VS Code server
        ]
        
        dev_commands = [
            # Configure Docker
            "usermod -aG docker ansible-admin",
            "systemctl enable docker",
            "systemctl start docker",
            
            # Open additional ports for development
            "ufw allow 8080",  # Common dev port
            "ufw allow 3000",  # Node.js dev server
            "ufw allow 8000"   # Python dev server
        ]
        
        config = cls.base_vm_config(
            hostname=hostname,
            additional_packages=dev_packages,
            additional_commands=dev_commands,
            **kwargs
        )
        
        return config
    
    @classmethod
    def docker_server_config(cls, hostname: str, **kwargs) -> Dict[str, Any]:
        """Cloud-init config for Docker-focused VMs."""
        docker_packages = [
            "docker.io",
            "docker-compose", 
            "docker-buildx",
            "nginx"  # Reverse proxy
        ]
        
        docker_commands = [
            # Docker configuration
            "usermod -aG docker ansible-admin",
            "systemctl enable docker",
            "systemctl start docker",
            
            # Docker daemon configuration for better performance
            "mkdir -p /etc/docker",
            """cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF""",
            "systemctl restart docker",
            
            # Install Docker Compose (latest version)
            "curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose",
            "chmod +x /usr/local/bin/docker-compose",
            
            # Open Docker/web ports
            "ufw allow 80",
            "ufw allow 443",
            "ufw allow 8080"
        ]
        
        config = cls.base_vm_config(
            hostname=hostname,
            additional_packages=docker_packages,
            additional_commands=docker_commands,
            **kwargs
        )
        
        return config
    
    @classmethod
    def ai_server_config(cls, hostname: str, **kwargs) -> Dict[str, Any]:
        """Cloud-init config for AI/ML server VMs."""
        ai_packages = [
            "python3-dev",
            "python3-venv",
            "nvidia-driver-535",  # NVIDIA drivers (if GPU)
            "nvidia-container-toolkit",
            "docker.io"
        ]
        
        ai_commands = [
            # Python/pip updates for AI
            "pip3 install --upgrade pip",
            "pip3 install torch torchvision torchaudio",
            "pip3 install transformers",
            "pip3 install ollama",
            
            # Docker for AI containers
            "usermod -aG docker ansible-admin",
            "systemctl enable docker",
            "systemctl start docker",
            
            # NVIDIA container runtime (if GPU available)
            "which nvidia-smi && nvidia-ctk runtime configure --runtime=docker || true",
            "which nvidia-smi && systemctl restart docker || true",
            
            # Open AI service ports
            "ufw allow 11434",  # Ollama
            "ufw allow 8080",   # Common AI UI port
            "ufw allow 7860"    # Gradio default
        ]
        
        config = cls.base_vm_config(
            hostname=hostname,
            additional_packages=ai_packages,
            additional_commands=ai_commands,
            **kwargs
        )
        
        return config
    
    @classmethod
    def web_server_config(cls, hostname: str, **kwargs) -> Dict[str, Any]:
        """Cloud-init config for web server VMs."""
        web_packages = [
            "nginx",
            "certbot",
            "python3-certbot-nginx",
            "php8.1-fpm",
            "php8.1-mysql",
            "mysql-client"
        ]
        
        web_commands = [
            # Nginx configuration
            "systemctl enable nginx",
            "systemctl start nginx",
            
            # PHP configuration
            "systemctl enable php8.1-fpm",
            "systemctl start php8.1-fpm",
            
            # Basic firewall for web server
            "ufw allow 'Nginx Full'",
            "ufw allow 80",
            "ufw allow 443"
        ]
        
        config = cls.base_vm_config(
            hostname=hostname,
            additional_packages=web_packages,
            additional_commands=web_commands,
            **kwargs
        )
        
        return config
    
    @classmethod
    def database_server_config(cls, hostname: str, **kwargs) -> Dict[str, Any]:
        """Cloud-init config for database server VMs."""
        db_packages = [
            "mysql-server",
            "postgresql", 
            "postgresql-contrib",
            "redis-server"
        ]
        
        db_commands = [
            # MySQL configuration
            "systemctl enable mysql",
            "systemctl start mysql",
            
            # PostgreSQL configuration  
            "systemctl enable postgresql",
            "systemctl start postgresql",
            
            # Redis configuration
            "systemctl enable redis-server",
            "systemctl start redis-server",
            
            # Database ports
            "ufw allow 3306",  # MySQL
            "ufw allow 5432",  # PostgreSQL
            "ufw allow 6379"   # Redis
        ]
        
        config = cls.base_vm_config(
            hostname=hostname,
            additional_packages=db_packages, 
            additional_commands=db_commands,
            **kwargs
        )
        
        return config


def get_cloud_init_config(vm_type: str, hostname: str, **kwargs) -> str:
    """
    Get cloud-init configuration YAML for specified VM type.
    
    Args:
        vm_type: Type of VM (base, development, docker, ai, web, database)
        hostname: VM hostname
        **kwargs: Additional configuration options
    
    Returns:
        YAML string ready for cloud-init
    """
    
    template_map = {
        "base": CloudInitTemplates.base_vm_config,
        "development": CloudInitTemplates.development_vm_config,
        "docker": CloudInitTemplates.docker_server_config,
        "ai": CloudInitTemplates.ai_server_config,
        "web": CloudInitTemplates.web_server_config,
        "database": CloudInitTemplates.database_server_config
    }
    
    if vm_type not in template_map:
        raise ValueError(f"Unknown VM type: {vm_type}. Available: {list(template_map.keys())}")
    
    config_func = template_map[vm_type]
    config = config_func(hostname=hostname, **kwargs)
    
    # Add cloud-init metadata
    config["#cloud-config"] = True
    
    return yaml.dump(config, default_flow_style=False, allow_unicode=True)