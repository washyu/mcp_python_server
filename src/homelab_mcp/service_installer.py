"""Service installation framework for homelab applications."""

import asyncio
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from .ssh_tools import ssh_execute_command

# Service templates directory
TEMPLATES_DIR = Path(__file__).parent / "service_templates"


class ServiceInstaller:
    """Framework for installing and managing homelab services."""
    
    def __init__(self):
        self.templates = self._load_service_templates()
    
    def _load_service_templates(self) -> Dict[str, Dict]:
        """Load all service templates from the templates directory."""
        templates = {}
        
        # Ensure templates directory exists
        TEMPLATES_DIR.mkdir(exist_ok=True)
        
        # Load YAML template files
        for template_file in TEMPLATES_DIR.glob("*.yaml"):
            try:
                with open(template_file, 'r') as f:
                    service_data = yaml.safe_load(f)
                    service_name = template_file.stem
                    templates[service_name] = service_data
            except Exception as e:
                print(f"Warning: Failed to load template {template_file}: {e}")
        
        return templates
    
    def get_available_services(self) -> List[str]:
        """Get list of available service templates."""
        return list(self.templates.keys())
    
    def get_service_info(self, service_name: str) -> Optional[Dict]:
        """Get detailed information about a service."""
        return self.templates.get(service_name)
    
    async def check_service_requirements(
        self, 
        service_name: str, 
        hostname: str, 
        username: str = "mcp_admin",
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check if a device meets the requirements for a service."""
        if service_name not in self.templates:
            return {"status": "error", "error": f"Unknown service: {service_name}"}
        
        service = self.templates[service_name]
        requirements = service.get("requirements", {})
        results = {
            "service": service_name,
            "hostname": hostname,
            "requirements_met": True,
            "checks": {}
        }
        
        # Check available ports
        if "ports" in requirements:
            for port in requirements["ports"]:
                # Check if port is available
                cmd = f"ss -tlnp | grep :{port}"
                port_result = await ssh_execute_command(
                    hostname=hostname,
                    username=username,
                    password=password,
                    command=cmd
                )
                
                port_data = json.loads(port_result)
                port_available = port_data.get("exit_code", 1) != 0  # Port is free if command fails
                results["checks"][f"port_{port}"] = {
                    "required": True,
                    "available": port_available,
                    "status": "pass" if port_available else "fail"
                }
                if not port_available:
                    results["requirements_met"] = False
        
        # Check available memory
        if "memory_gb" in requirements:
            cmd = "free -m | grep '^Mem:' | awk '{print $2}'"
            mem_result = await ssh_execute_command(
                hostname=hostname,
                username=username,
                password=password,
                command=cmd
            )
            
            mem_data = json.loads(mem_result)
            if mem_data.get("exit_code") == 0:
                available_mb = int(mem_data.get("output", "0").split("Output:\n")[-1])
                required_mb = requirements["memory_gb"] * 1024
                memory_ok = available_mb >= required_mb
                
                results["checks"]["memory"] = {
                    "required_mb": required_mb,
                    "available_mb": available_mb,
                    "status": "pass" if memory_ok else "fail"
                }
                if not memory_ok:
                    results["requirements_met"] = False
        
        # Check disk space
        if "disk_gb" in requirements:
            cmd = "df / | tail -1 | awk '{print $4}'"
            disk_result = await ssh_execute_command(
                hostname=hostname,
                username=username,
                password=password,
                command=cmd
            )
            
            disk_data = json.loads(disk_result)
            if disk_data.get("exit_code") == 0:
                available_kb = int(disk_data.get("output", "0").split("Output:\n")[-1])
                required_kb = requirements["disk_gb"] * 1024 * 1024
                disk_ok = available_kb >= required_kb
                
                results["checks"]["disk_space"] = {
                    "required_gb": requirements["disk_gb"],
                    "available_gb": round(available_kb / 1024 / 1024, 2),
                    "status": "pass" if disk_ok else "fail"
                }
                if not disk_ok:
                    results["requirements_met"] = False
        
        return results
    
    async def install_service(
        self,
        service_name: str,
        hostname: str,
        username: str = "mcp_admin",
        password: Optional[str] = None,
        config_override: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Install a service on the target device."""
        if service_name not in self.templates:
            return {"status": "error", "error": f"Unknown service: {service_name}"}
        
        service = self.templates[service_name]
        
        # Check requirements first
        req_check = await self.check_service_requirements(
            service_name, hostname, username, password
        )
        
        if not req_check["requirements_met"]:
            return {
                "status": "error",
                "error": "Requirements not met",
                "requirement_check": req_check
            }
        
        # Get installation method
        install_method = service.get("installation", {}).get("method", "docker-compose")
        
        if install_method == "docker-compose":
            return await self._install_docker_compose_service(
                service_name, service, hostname, username, password, config_override
            )
        elif install_method == "script":
            return await self._install_script_service(
                service_name, service, hostname, username, password, config_override
            )
        else:
            return {
                "status": "error",
                "error": f"Unsupported installation method: {install_method}"
            }
    
    async def _install_docker_compose_service(
        self,
        service_name: str,
        service: Dict,
        hostname: str,
        username: str,
        password: Optional[str],
        config_override: Optional[Dict]
    ) -> Dict[str, Any]:
        """Install a service using Docker Compose."""
        results = {
            "service": service_name,
            "hostname": hostname,
            "installation_method": "docker-compose",
            "steps": []
        }
        
        try:
            # Step 1: Ensure Docker is installed
            docker_check = await ssh_execute_command(
                hostname=hostname,
                username=username,
                password=password,
                command="docker --version"
            )
            
            docker_data = json.loads(docker_check)
            if docker_data.get("exit_code") != 0:
                results["steps"].append({
                    "step": "check_docker",
                    "status": "fail",
                    "error": "Docker not installed"
                })
                return {"status": "error", "results": results}
            
            results["steps"].append({
                "step": "check_docker",
                "status": "success"
            })
            
            # Step 2: Ensure Docker Compose is available
            compose_check = await ssh_execute_command(
                hostname=hostname,
                username=username,
                password=password,
                command="docker compose version"
            )
            
            compose_data = json.loads(compose_check)
            if compose_data.get("exit_code") != 0:
                results["steps"].append({
                    "step": "check_docker_compose",
                    "status": "fail",
                    "error": "Docker Compose not available"
                })
                return {"status": "error", "results": results}
            
            results["steps"].append({
                "step": "check_docker_compose",
                "status": "success"
            })
            
            # Step 3: Create service directory
            service_dir = f"/opt/{service_name}"
            mkdir_result = await ssh_execute_command(
                hostname=hostname,
                username=username,
                password=password,
                command=f"sudo mkdir -p {service_dir}",
                sudo=False  # sudo is included in command
            )
            
            mkdir_data = json.loads(mkdir_result)
            if mkdir_data.get("exit_code") != 0:
                results["steps"].append({
                    "step": "create_directory",
                    "status": "fail",
                    "error": f"Failed to create {service_dir}"
                })
                return {"status": "error", "results": results}
            
            results["steps"].append({
                "step": "create_directory",
                "status": "success",
                "directory": service_dir
            })
            
            # Step 4: Generate docker-compose.yml
            compose_content = service["installation"]["docker_compose"]
            
            # Apply configuration overrides
            if config_override:
                # Simple merge for now - could be more sophisticated
                compose_content = self._merge_config(compose_content, config_override)
            
            # Write docker-compose.yml to remote system
            compose_yaml = yaml.dump(compose_content, default_flow_style=False)
            write_compose = await ssh_execute_command(
                hostname=hostname,
                username=username,
                password=password,
                command=f"sudo tee {service_dir}/docker-compose.yml > /dev/null << 'EOF'\n{compose_yaml}\nEOF"
            )
            
            write_data = json.loads(write_compose)
            if write_data.get("exit_code") != 0:
                results["steps"].append({
                    "step": "write_compose_file",
                    "status": "fail",
                    "error": "Failed to write docker-compose.yml"
                })
                return {"status": "error", "results": results}
            
            results["steps"].append({
                "step": "write_compose_file",
                "status": "success"
            })
            
            # Step 5: Start the service
            start_result = await ssh_execute_command(
                hostname=hostname,
                username=username,
                password=password,
                command=f"cd {service_dir} && sudo docker compose up -d"
            )
            
            start_data = json.loads(start_result)
            if start_data.get("exit_code") != 0:
                results["steps"].append({
                    "step": "start_service",
                    "status": "fail",
                    "error": f"Failed to start service: {start_data.get('output', '')}"
                })
                return {"status": "error", "results": results}
            
            results["steps"].append({
                "step": "start_service",
                "status": "success",
                "output": start_data.get("output", "")
            })
            
            # Step 6: Verify service is running
            status_result = await ssh_execute_command(
                hostname=hostname,
                username=username,
                password=password,
                command=f"cd {service_dir} && sudo docker compose ps"
            )
            
            status_data = json.loads(status_result)
            results["steps"].append({
                "step": "verify_service",
                "status": "success" if status_data.get("exit_code") == 0 else "warning",
                "container_status": status_data.get("output", "")
            })
            
            return {
                "status": "success",
                "service": service_name,
                "hostname": hostname,
                "access_url": f"http://{hostname}:{service.get('default_port', 8080)}",
                "installation_directory": service_dir,
                "results": results
            }
            
        except Exception as e:
            results["steps"].append({
                "step": "exception",
                "status": "fail",
                "error": str(e)
            })
            return {"status": "error", "results": results}
    
    async def _install_script_service(
        self,
        service_name: str,
        service: Dict,
        hostname: str,
        username: str,
        password: Optional[str],
        config_override: Optional[Dict]
    ) -> Dict[str, Any]:
        """Install a service using shell scripts."""
        # TODO: Implement script-based installation
        return {
            "status": "error",
            "error": "Script-based installation not yet implemented"
        }
    
    def _merge_config(self, base_config: Dict, override: Dict) -> Dict:
        """Merge configuration override with base configuration."""
        # Simple recursive merge - could be enhanced
        result = base_config.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    async def get_service_status(
        self,
        service_name: str,
        hostname: str,
        username: str = "mcp_admin",
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get the current status of an installed service."""
        service_dir = f"/opt/{service_name}"
        
        # Check if service directory exists
        dir_check = await ssh_execute_command(
            hostname=hostname,
            username=username,
            password=password,
            command=f"test -d {service_dir}"
        )
        
        dir_data = json.loads(dir_check)
        if dir_data.get("exit_code") != 0:
            return {
                "status": "not_installed",
                "service": service_name,
                "hostname": hostname
            }
        
        # Check container status
        status_result = await ssh_execute_command(
            hostname=hostname,
            username=username,
            password=password,
            command=f"cd {service_dir} && sudo docker compose ps --format json"
        )
        
        status_data = json.loads(status_result)
        
        return {
            "status": "installed",
            "service": service_name,
            "hostname": hostname,
            "container_status": status_data.get("output", ""),
            "service_directory": service_dir
        }