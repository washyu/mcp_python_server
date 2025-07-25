"""Package manager for homelab services - Scoop-like functionality."""

import asyncio
import json
import yaml
import hashlib
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse
import httpx
from datetime import datetime

from .service_installer import ServiceInstaller
from .config import get_config, MCPConfig


class PackageRegistry:
    """Manages package sources and registry indexes."""
    
    def __init__(self, config: Optional[MCPConfig] = None):
        self.config = config or get_config()
        self.sources = self._load_sources()
        self.cache_dir = Path.home() / ".mcp" / "package_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_sources(self) -> Dict[str, str]:
        """Load package sources from configuration."""
        sources_file = Path.home() / ".mcp" / "sources.json"
        
        if sources_file.exists():
            with open(sources_file, 'r') as f:
                return json.load(f)
        
        # Default sources
        return {
            "official": "https://github.com/homelab-mcp/packages",
            "community": "https://github.com/homelab-community/packages"
        }
    
    def add_source(self, name: str, url: str) -> None:
        """Add a new package source."""
        self.sources[name] = url
        self._save_sources()
    
    def remove_source(self, name: str) -> None:
        """Remove a package source."""
        if name in self.sources:
            del self.sources[name]
            self._save_sources()
    
    def _save_sources(self) -> None:
        """Save sources to configuration file."""
        sources_file = Path.home() / ".mcp" / "sources.json"
        with open(sources_file, 'w') as f:
            json.dump(self.sources, f, indent=2)
    
    async def fetch_registry(self, source_name: str) -> Dict[str, Any]:
        """Fetch registry index from a package source."""
        if source_name not in self.sources:
            raise ValueError(f"Unknown source: {source_name}")
        
        source_url = self.sources[source_name]
        registry_url = f"{source_url}/raw/main/registry.json"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(registry_url)
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to fetch registry from {source_name}: {response.status_code}")
    
    async def search_packages(self, query: str, tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search for packages across all sources."""
        results = []
        
        for source_name in self.sources:
            try:
                registry = await self.fetch_registry(source_name)
                packages = registry.get("packages", {})
                
                for pkg_name, pkg_info in packages.items():
                    # Search by name and description
                    if query.lower() in pkg_name.lower() or \
                       query.lower() in pkg_info.get("description", "").lower():
                        
                        # Filter by tags if specified
                        if tags:
                            pkg_tags = pkg_info.get("tags", [])
                            if not any(tag in pkg_tags for tag in tags):
                                continue
                        
                        results.append({
                            "name": pkg_name,
                            "version": pkg_info.get("latest"),
                            "description": pkg_info.get("description"),
                            "source": source_name,
                            "tags": pkg_info.get("tags", [])
                        })
            except Exception as e:
                print(f"Warning: Failed to search {source_name}: {e}")
        
        return results


class PackageManager:
    """Main package manager for installing homelab services."""
    
    def __init__(self):
        self.registry = PackageRegistry()
        self.service_installer = ServiceInstaller()
        self.installed_packages = self._load_installed_packages()
    
    def _load_installed_packages(self) -> Dict[str, Dict[str, Any]]:
        """Load list of installed packages."""
        installed_file = Path.home() / ".mcp" / "installed_packages.json"
        
        if installed_file.exists():
            with open(installed_file, 'r') as f:
                return json.load(f)
        
        return {}
    
    def _save_installed_packages(self) -> None:
        """Save installed packages list."""
        installed_file = Path.home() / ".mcp" / "installed_packages.json"
        installed_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(installed_file, 'w') as f:
            json.dump(self.installed_packages, f, indent=2)
    
    async def fetch_manifest(self, package_name: str, version: str = "latest", source: str = "official") -> Dict[str, Any]:
        """Fetch package manifest from repository."""
        registry = await self.registry.fetch_registry(source)
        packages = registry.get("packages", {})
        
        if package_name not in packages:
            raise ValueError(f"Package '{package_name}' not found in {source}")
        
        pkg_info = packages[package_name]
        
        # Resolve version
        if version == "latest":
            version = pkg_info.get("latest")
        elif version not in pkg_info.get("versions", []):
            raise ValueError(f"Version '{version}' not found for package '{package_name}'")
        
        # Fetch manifest
        manifest_path = pkg_info.get("manifest", f"packages/{package_name}/manifest.yaml")
        manifest_url = f"{self.registry.sources[source]}/raw/main/{manifest_path}"
        
        # Check for version-specific manifest
        if version != pkg_info.get("latest"):
            version_manifest_url = f"{self.registry.sources[source]}/raw/main/packages/{package_name}/versions/{version}.yaml"
            try:
                manifest = await self._fetch_yaml(version_manifest_url)
                manifest["_source"] = source
                manifest["_source_url"] = self.registry.sources[source]
                return manifest
            except:
                pass  # Fall back to main manifest
        
        manifest = await self._fetch_yaml(manifest_url)
        manifest["_source"] = source
        manifest["_source_url"] = self.registry.sources[source]
        return manifest
    
    async def _fetch_yaml(self, url: str) -> Dict[str, Any]:
        """Fetch and parse YAML from URL."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                content = response.text
                return yaml.safe_load(content)
            else:
                raise Exception(f"Failed to fetch {url}: {response.status_code}")
    
    async def _fetch_file(self, url: str, dest_path: Path) -> None:
        """Download file from URL to destination."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                content = response.content
                with open(dest_path, 'wb') as f:
                    f.write(content)
            else:
                raise Exception(f"Failed to download {url}: {response.status_code}")
    
    def _validate_manifest(self, manifest: Dict[str, Any]) -> List[str]:
        """Validate package manifest structure."""
        errors = []
        required_fields = ["name", "version", "description", "install"]
        
        for field in required_fields:
            if field not in manifest:
                errors.append(f"Missing required field: {field}")
        
        if "install" in manifest:
            install = manifest["install"]
            if "method" not in install:
                errors.append("Missing install.method field")
            elif install["method"] not in ["docker-compose", "script", "terraform", "ansible"]:
                errors.append(f"Unknown install method: {install['method']}")
        
        return errors
    
    async def install(
        self,
        package_name: str,
        hostname: str,
        username: str = "mcp_admin",
        password: Optional[str] = None,
        version: str = "latest",
        source: str = "official",
        config_override: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Install a package from the repository."""
        # Check if already installed
        host_packages = self.installed_packages.get(hostname, {})
        if package_name in host_packages:
            installed_version = host_packages[package_name]["version"]
            if installed_version == version or (version == "latest" and installed_version == host_packages[package_name].get("latest_version")):
                return {
                    "status": "info",
                    "message": f"Package '{package_name}' version '{installed_version}' is already installed"
                }
        
        # Fetch manifest
        try:
            manifest = await self.fetch_manifest(package_name, version, source)
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to fetch manifest: {str(e)}"
            }
        
        # Validate manifest
        errors = self._validate_manifest(manifest)
        if errors:
            return {
                "status": "error",
                "error": "Invalid manifest",
                "validation_errors": errors
            }
        
        # Download package assets if needed
        install_config = manifest.get("install", {})
        method = install_config.get("method")
        
        # Prepare configuration
        final_config = manifest.get("default_config", {}).copy()
        if config_override:
            final_config.update(config_override)
        
        # Convert manifest to service template format
        service_template = self._manifest_to_service_template(manifest, final_config)
        
        # Add to service installer templates
        self.service_installer.templates[package_name] = service_template
        
        # Install using service installer
        result = await self.service_installer.install_service(
            service_name=package_name,
            hostname=hostname,
            username=username,
            password=password,
            config_override=final_config
        )
        
        # Record installation if successful
        if result.get("status") == "success":
            if hostname not in self.installed_packages:
                self.installed_packages[hostname] = {}
            
            self.installed_packages[hostname][package_name] = {
                "version": manifest["version"],
                "latest_version": manifest["version"],
                "source": source,
                "installed_at": datetime.now().isoformat(),
                "config": final_config
            }
            self._save_installed_packages()
        
        return result
    
    def _manifest_to_service_template(self, manifest: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert package manifest to service template format."""
        install = manifest.get("install", {})
        
        template = {
            "name": manifest.get("name"),
            "description": manifest.get("description"),
            "version": manifest.get("version"),
            "homepage": manifest.get("homepage"),
            "requirements": manifest.get("requirements", {}),
            "default_port": manifest.get("default_port", 8080),
            "default_config": config,
            "installation": {
                "method": install.get("method", "docker-compose")
            }
        }
        
        # Add method-specific configuration
        method = install.get("method")
        if method == "docker-compose":
            template["installation"]["docker_compose"] = install.get("compose", {})
        elif method == "terraform":
            template["installation"]["terraform"] = install.get("terraform", {})
        elif method == "ansible":
            template["installation"]["ansible"] = install.get("ansible", {})
        elif method == "script":
            template["installation"]["script"] = install.get("script", {})
        
        return template
    
    async def list_installed(self, hostname: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """List installed packages."""
        if hostname:
            return self.installed_packages.get(hostname, {})
        return self.installed_packages
    
    async def update(
        self,
        package_name: str,
        hostname: str,
        username: str = "mcp_admin",
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update an installed package to the latest version."""
        host_packages = self.installed_packages.get(hostname, {})
        
        if package_name not in host_packages:
            return {
                "status": "error",
                "error": f"Package '{package_name}' is not installed on {hostname}"
            }
        
        installed_info = host_packages[package_name]
        source = installed_info.get("source", "official")
        
        # Check for updates
        try:
            manifest = await self.fetch_manifest(package_name, "latest", source)
            latest_version = manifest["version"]
            current_version = installed_info["version"]
            
            if latest_version == current_version:
                return {
                    "status": "info",
                    "message": f"Package '{package_name}' is already at the latest version ({current_version})"
                }
            
            # Perform update
            config = installed_info.get("config", {})
            result = await self.install(
                package_name=package_name,
                hostname=hostname,
                username=username,
                password=password,
                version="latest",
                source=source,
                config_override=config
            )
            
            if result.get("status") == "success":
                result["message"] = f"Updated {package_name} from {current_version} to {latest_version}"
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to update package: {str(e)}"
            }
    
    async def remove(
        self,
        package_name: str,
        hostname: str,
        username: str = "mcp_admin",
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """Remove an installed package."""
        host_packages = self.installed_packages.get(hostname, {})
        
        if package_name not in host_packages:
            return {
                "status": "error",
                "error": f"Package '{package_name}' is not installed on {hostname}"
            }
        
        # For now, we'll use the existing service status check
        # In the future, this should properly uninstall the service
        status = await self.service_installer.get_service_status(
            service_name=package_name,
            hostname=hostname,
            username=username,
            password=password
        )
        
        if status.get("status") == "not_installed":
            # Remove from installed packages
            del self.installed_packages[hostname][package_name]
            if not self.installed_packages[hostname]:
                del self.installed_packages[hostname]
            self._save_installed_packages()
            
            return {
                "status": "success",
                "message": f"Package '{package_name}' removed from {hostname}"
            }
        
        return {
            "status": "info",
            "message": f"Package '{package_name}' needs manual removal",
            "service_status": status
        }


# MCP Tool Functions
async def package_search(query: str, tags: Optional[List[str]] = None) -> str:
    """Search for packages in the registry."""
    pm = PackageManager()
    results = await pm.registry.search_packages(query, tags)
    
    if not results:
        return json.dumps({
            "status": "info",
            "message": f"No packages found matching '{query}'",
            "results": []
        })
    
    return json.dumps({
        "status": "success",
        "message": f"Found {len(results)} packages",
        "results": results
    })


async def package_info(name: str, version: str = "latest", source: str = "official") -> str:
    """Get detailed information about a package."""
    pm = PackageManager()
    
    try:
        manifest = await pm.fetch_manifest(name, version, source)
        return json.dumps({
            "status": "success",
            "package": manifest
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e)
        })


async def package_install(
    name: str,
    hostname: str,
    username: str = "mcp_admin",
    password: Optional[str] = None,
    version: str = "latest",
    source: str = "official",
    config: Optional[Dict] = None
) -> str:
    """Install a package from the registry."""
    pm = PackageManager()
    result = await pm.install(
        package_name=name,
        hostname=hostname,
        username=username,
        password=password,
        version=version,
        source=source,
        config_override=config
    )
    return json.dumps(result)


async def package_list(hostname: Optional[str] = None) -> str:
    """List installed packages."""
    pm = PackageManager()
    packages = await pm.list_installed(hostname)
    
    return json.dumps({
        "status": "success",
        "packages": packages
    })


async def package_update(
    name: str,
    hostname: str,
    username: str = "mcp_admin",
    password: Optional[str] = None
) -> str:
    """Update an installed package."""
    pm = PackageManager()
    result = await pm.update(
        package_name=name,
        hostname=hostname,
        username=username,
        password=password
    )
    return json.dumps(result)


async def package_remove(
    name: str,
    hostname: str,
    username: str = "mcp_admin",
    password: Optional[str] = None
) -> str:
    """Remove an installed package."""
    pm = PackageManager()
    result = await pm.remove(
        package_name=name,
        hostname=hostname,
        username=username,
        password=password
    )
    return json.dumps(result)


async def package_source_add(name: str, url: str) -> str:
    """Add a new package source."""
    pm = PackageManager()
    pm.registry.add_source(name, url)
    
    return json.dumps({
        "status": "success",
        "message": f"Added package source '{name}' -> {url}",
        "sources": pm.registry.sources
    })


async def package_source_remove(name: str) -> str:
    """Remove a package source."""
    pm = PackageManager()
    
    if name == "official":
        return json.dumps({
            "status": "error",
            "error": "Cannot remove the official package source"
        })
    
    if name not in pm.registry.sources:
        return json.dumps({
            "status": "error",
            "error": f"Source '{name}' not found"
        })
    
    pm.registry.remove_source(name)
    
    return json.dumps({
        "status": "success",
        "message": f"Removed package source '{name}'",
        "sources": pm.registry.sources
    })


async def package_source_list() -> str:
    """List all package sources."""
    pm = PackageManager()
    
    return json.dumps({
        "status": "success",
        "sources": pm.registry.sources
    })