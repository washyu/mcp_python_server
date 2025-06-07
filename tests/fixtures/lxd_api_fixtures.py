"""
Test fixtures and mocks for LXD API responses.
Provides realistic mock data for LXD API endpoints to support TDD development.
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock

# LXD API Response Fixtures

class LXDAPIFixtures:
    """Collection of LXD API response fixtures for testing."""
    
    @staticmethod
    def server_info() -> Dict[str, Any]:
        """Mock LXD server information response."""
        return {
            "api_status": "stable",
            "api_status_code": 200,
            "api_version": "1.0",
            "auth": "trusted",
            "config": {
                "core.https_address": "[::]",
                "core.trust_password": True
            },
            "environment": {
                "addresses": ["192.168.10.101:8443"],
                "architectures": ["aarch64", "armhf"],
                "certificate": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
                "certificate_fingerprint": "abc123def456",
                "driver": "lxc",
                "driver_version": "5.0.2",
                "firewall": "xtables",
                "kernel": "Linux",
                "kernel_architecture": "aarch64",
                "kernel_version": "6.1.0-rpi4-rpi-v8",
                "lxc_version": "5.0.2",
                "os_name": "Ubuntu",
                "os_version": "22.04",
                "project": "default",
                "server": "lxd",
                "server_clustered": True,
                "server_name": "pi-01",
                "server_pid": 1234,
                "server_version": "5.0.2",
                "storage": "dir",
                "storage_version": "1"
            },
            "public": False
        }
    
    @staticmethod
    def containers_list() -> List[Dict[str, Any]]:
        """Mock container list response."""
        return [
            {
                "architecture": "aarch64",
                "config": {
                    "image.architecture": "aarch64",
                    "image.description": "Ubuntu 22.04 LTS arm64",
                    "image.os": "ubuntu",
                    "image.release": "jammy",
                    "image.version": "22.04",
                    "limits.cpu": "2",
                    "limits.memory": "2GB",
                    "volatile.base_image": "abc123def456",
                    "volatile.eth0.hwaddr": "00:16:3e:01:02:03",
                    "volatile.idmap.base": "0",
                    "volatile.idmap.current": "[{\"Isuid\":true,\"Isgid\":false,\"Hostid\":1000000,\"Nsid\":0,\"Maprange\":1000000000}]",
                    "volatile.last_state.idmap": "[{\"Isuid\":true,\"Isgid\":false,\"Hostid\":1000000,\"Nsid\":0,\"Maprange\":1000000000}]",
                    "volatile.last_state.power": "RUNNING"
                },
                "created_at": "2024-01-30T09:00:00Z",
                "description": "Web server container",
                "devices": {
                    "eth0": {
                        "name": "eth0",
                        "network": "lxdbr0",
                        "type": "nic"
                    },
                    "root": {
                        "path": "/",
                        "pool": "default",
                        "type": "disk"
                    }
                },
                "ephemeral": False,
                "expanded_config": {
                    "image.architecture": "aarch64",
                    "limits.cpu": "2",
                    "limits.memory": "2GB"
                },
                "expanded_devices": {
                    "eth0": {
                        "name": "eth0",
                        "network": "lxdbr0",
                        "type": "nic"
                    },
                    "root": {
                        "path": "/",
                        "pool": "default",
                        "type": "disk"
                    }
                },
                "last_used_at": "2024-01-30T10:30:00Z",
                "location": "pi-01",
                "name": "web-server",
                "profiles": ["default", "web-profile"],
                "project": "default",
                "restore": "",
                "stateful": False,
                "status": "running",
                "status_code": 103,
                "type": "container"
            },
            {
                "architecture": "aarch64",
                "config": {
                    "image.architecture": "aarch64",
                    "image.description": "Ubuntu 20.04 LTS arm64",
                    "image.os": "ubuntu",
                    "image.release": "focal",
                    "image.version": "20.04",
                    "limits.cpu": "4",
                    "limits.memory": "4GB"
                },
                "created_at": "2024-01-29T15:00:00Z",
                "description": "Database server container",
                "devices": {
                    "eth0": {
                        "name": "eth0",
                        "network": "lxdbr0",
                        "type": "nic"
                    },
                    "root": {
                        "path": "/",
                        "pool": "default",
                        "type": "disk"
                    },
                    "data": {
                        "path": "/var/lib/mysql",
                        "pool": "ssd-pool",
                        "type": "disk"
                    }
                },
                "ephemeral": False,
                "last_used_at": "2024-01-30T10:25:00Z",
                "location": "pi-02",
                "name": "database",
                "profiles": ["default", "db-profile"],
                "project": "default",
                "stateful": False,
                "status": "stopped",
                "status_code": 102,
                "type": "container"
            },
            {
                "architecture": "aarch64",
                "config": {
                    "image.architecture": "aarch64",
                    "image.description": "Alpine Linux 3.19 arm64",
                    "image.os": "alpine",
                    "image.release": "3.19",
                    "limits.cpu": "1",
                    "limits.memory": "512MB"
                },
                "created_at": "2024-01-30T08:00:00Z",
                "description": "Lightweight development environment",
                "devices": {
                    "eth0": {
                        "name": "eth0",
                        "network": "lxdbr0",
                        "type": "nic"
                    },
                    "root": {
                        "path": "/",
                        "pool": "default",
                        "type": "disk"
                    }
                },
                "ephemeral": True,
                "last_used_at": "2024-01-30T10:00:00Z",
                "location": "pi-01",
                "name": "dev-env",
                "profiles": ["default"],
                "project": "default",
                "stateful": False,
                "status": "running",
                "status_code": 103,
                "type": "container"
            }
        ]
    
    @staticmethod
    def container_state(name: str = "web-server") -> Dict[str, Any]:
        """Mock container state response."""
        if name == "web-server":
            return {
                "status": "running",
                "status_code": 103,
                "disk": {
                    "root": {
                        "usage": 1073741824  # 1GB
                    }
                },
                "memory": {
                    "usage": 536870912,      # 512MB
                    "usage_peak": 1073741824, # 1GB
                    "swap_usage": 0,
                    "swap_usage_peak": 0
                },
                "network": {
                    "eth0": {
                        "addresses": [
                            {
                                "family": "inet",
                                "address": "10.0.0.10",
                                "netmask": "24",
                                "scope": "global"
                            },
                            {
                                "family": "inet6",
                                "address": "fd42:4c81:5770:1eaf:216:3eff:fe01:203",
                                "netmask": "64",
                                "scope": "global"
                            }
                        ],
                        "counters": {
                            "bytes_received": 1234567890,
                            "bytes_sent": 987654321,
                            "packets_received": 123456,
                            "packets_sent": 98765
                        },
                        "hwaddr": "00:16:3e:01:02:03",
                        "host_name": "vethab12cd34",
                        "mtu": 1500,
                        "state": "up",
                        "type": "broadcast"
                    }
                },
                "pid": 1234,
                "processes": 23,
                "cpu": {
                    "usage": 150000000  # nanoseconds
                }
            }
        elif name == "database":
            return {
                "status": "stopped",
                "status_code": 102,
                "disk": {},
                "memory": {},
                "network": {},
                "pid": -1,
                "processes": -1,
                "cpu": {}
            }
        else:
            return {
                "status": "running",
                "status_code": 103,
                "memory": {"usage": 268435456},  # 256MB
                "cpu": {"usage": 50000000}
            }
    
    @staticmethod
    def images_list() -> List[Dict[str, Any]]:
        """Mock images list response."""
        return [
            {
                "aliases": [
                    {
                        "description": "Ubuntu 22.04 LTS arm64",
                        "name": "ubuntu:22.04"
                    },
                    {
                        "description": "Ubuntu 22.04 LTS arm64", 
                        "name": "u2204"
                    }
                ],
                "architecture": "aarch64",
                "auto_update": True,
                "cached": False,
                "created_at": "2024-01-30T08:00:00Z",
                "expires_at": "2024-07-30T08:00:00Z",
                "filename": "ubuntu-22.04-server-cloudimg-arm64-lxd.tar.xz",
                "fingerprint": "abc123def456ghi789jkl012mno345pqr678stu901vwx234yzab567cde890fgh123",
                "last_used_at": "2024-01-30T09:00:00Z",
                "properties": {
                    "architecture": "aarch64",
                    "description": "Ubuntu 22.04 LTS arm64 (20240130_07:42)",
                    "label": "release",
                    "os": "ubuntu",
                    "release": "jammy",
                    "serial": "20240130_07:42",
                    "version": "22.04"
                },
                "public": False,
                "size": 157286400,
                "type": "container",
                "uploaded_at": "2024-01-30T08:00:00Z"
            },
            {
                "aliases": [
                    {
                        "description": "Alpine Linux 3.19 arm64",
                        "name": "alpine:3.19"
                    }
                ],
                "architecture": "aarch64",
                "auto_update": True,
                "cached": False,
                "created_at": "2024-01-30T07:00:00Z",
                "expires_at": "2024-07-30T07:00:00Z",
                "filename": "alpine-3.19-arm64-default_20240130_13:00.tar.xz",
                "fingerprint": "def456ghi789jkl012mno345pqr678stu901vwx234yzab567cde890fgh123abc456",
                "last_used_at": "2024-01-30T08:00:00Z",
                "properties": {
                    "architecture": "aarch64",
                    "description": "Alpine Linux 3.19 arm64 (20240130_13:00)",
                    "label": "release",
                    "os": "alpine",
                    "release": "3.19",
                    "serial": "20240130_13:00",
                    "version": "3.19"
                },
                "public": False,
                "size": 52428800,
                "type": "container",
                "uploaded_at": "2024-01-30T07:00:00Z"
            }
        ]
    
    @staticmethod
    def networks_list() -> List[Dict[str, Any]]:
        """Mock networks list response."""
        return [
            {
                "config": {
                    "ipv4.address": "10.0.0.1/24",
                    "ipv4.dhcp": "true",
                    "ipv4.dhcp.ranges": "10.0.0.2-10.0.0.254",
                    "ipv4.nat": "true",
                    "ipv6.address": "fd42:4c81:5770:1eaf::1/64",
                    "ipv6.dhcp": "true",
                    "ipv6.dhcp.stateful": "false",
                    "ipv6.nat": "true"
                },
                "description": "Default LXD bridge network",
                "locations": ["pi-01", "pi-02"],
                "managed": True,
                "name": "lxdbr0",
                "status": "Created",
                "type": "bridge",
                "used_by": [
                    "/1.0/instances/web-server",
                    "/1.0/instances/database",
                    "/1.0/instances/dev-env"
                ]
            },
            {
                "config": {
                    "parent": "eth0"
                },
                "description": "External network bridge",
                "locations": ["pi-01"],
                "managed": True,
                "name": "macvlan0",
                "status": "Created",
                "type": "macvlan",
                "used_by": []
            }
        ]
    
    @staticmethod
    def storage_pools_list() -> List[Dict[str, Any]]:
        """Mock storage pools list response."""
        return [
            {
                "config": {
                    "source": "/var/snap/lxd/common/lxd/storage-pools/default"
                },
                "description": "Default directory storage pool",
                "driver": "dir",
                "locations": ["pi-01", "pi-02"],
                "name": "default",
                "status": "Created",
                "used_by": [
                    "/1.0/instances/web-server",
                    "/1.0/instances/database", 
                    "/1.0/instances/dev-env",
                    "/1.0/images/abc123def456",
                    "/1.0/images/def456ghi789"
                ]
            },
            {
                "config": {
                    "source": "tank/lxd",
                    "zfs.pool_name": "tank"
                },
                "description": "ZFS storage pool for high performance workloads",
                "driver": "zfs",
                "locations": ["pi-02"],
                "name": "ssd-pool",
                "status": "Created",
                "used_by": [
                    "/1.0/instances/database"
                ]
            }
        ]
    
    @staticmethod
    def storage_pool_resources(pool_name: str = "default") -> Dict[str, Any]:
        """Mock storage pool resources response."""
        if pool_name == "default":
            return {
                "space": {
                    "used": 5368709120,      # 5GB
                    "total": 107374182400    # 100GB
                },
                "inodes": {
                    "used": 1234,
                    "total": 6553600
                }
            }
        elif pool_name == "ssd-pool":
            return {
                "space": {
                    "used": 2147483648,      # 2GB
                    "total": 53687091200     # 50GB
                },
                "inodes": {
                    "used": 567,
                    "total": 3276800
                }
            }
        else:
            return {
                "space": {"used": 0, "total": 0},
                "inodes": {"used": 0, "total": 0}
            }
    
    @staticmethod
    def cluster_members() -> List[Dict[str, Any]]:
        """Mock cluster members response."""
        return [
            {
                "server_name": "pi-01",
                "url": "https://192.168.10.101:8443",
                "database": True,
                "status": "Online",
                "message": "Fully operational",
                "architecture": "aarch64",
                "failure_domain": "rack1",
                "description": "Raspberry Pi 4 - Primary cluster member",
                "config": {
                    "scheduler.instance": "all"
                },
                "groups": ["default"]
            },
            {
                "server_name": "pi-02", 
                "url": "https://192.168.10.102:8443",
                "database": False,
                "status": "Online",
                "message": "Fully operational",
                "architecture": "aarch64",
                "failure_domain": "rack1",
                "description": "Raspberry Pi 4 - Secondary cluster member",
                "config": {
                    "scheduler.instance": "all"
                },
                "groups": ["default"]
            }
        ]
    
    @staticmethod
    def container_snapshots(container_name: str = "web-server") -> List[Dict[str, Any]]:
        """Mock container snapshots response."""
        return [
            {
                "architecture": "aarch64",
                "config": {
                    "image.architecture": "aarch64",
                    "limits.cpu": "2",
                    "limits.memory": "2GB"
                },
                "created_at": "2024-01-30T09:30:00Z",
                "description": "Snapshot before update",
                "devices": {
                    "eth0": {
                        "name": "eth0",
                        "network": "lxdbr0",
                        "type": "nic"
                    },
                    "root": {
                        "path": "/",
                        "pool": "default",
                        "type": "disk"
                    }
                },
                "ephemeral": False,
                "last_used_at": "2024-01-30T09:30:00Z",
                "location": "pi-01",
                "name": "before-update",
                "profiles": ["default", "web-profile"],
                "project": "default",
                "restore": "",
                "stateful": False,
                "type": "snapshot",
                "size": 1073741824  # 1GB
            },
            {
                "architecture": "aarch64", 
                "config": {
                    "image.architecture": "aarch64",
                    "limits.cpu": "2",
                    "limits.memory": "2GB"
                },
                "created_at": "2024-01-30T11:00:00Z",
                "description": "Snapshot after configuration changes",
                "devices": {
                    "eth0": {
                        "name": "eth0",
                        "network": "lxdbr0",
                        "type": "nic"
                    },
                    "root": {
                        "path": "/",
                        "pool": "default",
                        "type": "disk"
                    }
                },
                "ephemeral": False,
                "last_used_at": "2024-01-30T11:00:00Z",
                "location": "pi-01",
                "name": "after-config",
                "profiles": ["default", "web-profile"],
                "project": "default",
                "restore": "",
                "stateful": False,
                "type": "snapshot",
                "size": 1048576000  # ~1GB
            }
        ]
    
    @staticmethod
    def operation_status(operation_id: str) -> Dict[str, Any]:
        """Mock operation status response."""
        return {
            "id": operation_id,
            "class": "task",
            "description": "Creating container",
            "created_at": "2024-01-30T10:00:00Z",
            "updated_at": "2024-01-30T10:00:30Z",
            "status": "Success",
            "status_code": 200,
            "resources": {
                "containers": ["/1.0/containers/new-container"]
            },
            "metadata": {
                "id": operation_id,
                "class": "task",
                "description": "Creating container",
                "created_at": "2024-01-30T10:00:00Z",
                "updated_at": "2024-01-30T10:00:30Z",
                "status": "Success",
                "status_code": 200,
                "location": "pi-01",
                "may_cancel": False,
                "err": ""
            },
            "may_cancel": False,
            "err": "",
            "location": "pi-01"
        }
    
    @staticmethod
    def container_logs(container_name: str = "web-server") -> str:
        """Mock container logs response."""
        return """2024-01-30 09:00:00 INFO: Container starting up
2024-01-30 09:00:01 INFO: Initializing system services
2024-01-30 09:00:02 INFO: Starting networking
2024-01-30 09:00:03 INFO: Network interface eth0 configured
2024-01-30 09:00:04 INFO: Starting SSH daemon
2024-01-30 09:00:05 INFO: SSH daemon listening on port 22
2024-01-30 09:00:06 INFO: Starting web server
2024-01-30 09:00:07 INFO: Nginx started successfully
2024-01-30 09:00:08 INFO: Web server listening on port 80
2024-01-30 09:00:09 INFO: Container startup complete
2024-01-30 10:30:15 INFO: Health check passed
2024-01-30 10:30:30 INFO: Serving HTTP request from 192.168.10.50"""
    
    @staticmethod
    def exec_result(command: str = "ls -la") -> Dict[str, Any]:
        """Mock command execution result."""
        if command == "ls -la":
            return {
                "exit_code": 0,
                "stdout": "total 12\ndrwxr-xr-x 3 root root 4096 Jan 30 10:00 .\ndrwxr-xr-x 3 root root 4096 Jan 30 09:00 ..\ndrwxr-xr-x 2 root root 4096 Jan 30 10:00 test\n",
                "stderr": ""
            }
        elif command == "ps aux":
            return {
                "exit_code": 0,
                "stdout": "USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\nroot         1  0.0  0.1  23456  1234 ?        Ss   09:00   0:00 /sbin/init\nroot       123  0.1  0.5  67890  5678 ?        S    09:00   0:01 nginx: master process\nwww-data   124  0.0  0.3  45678  3456 ?        S    09:00   0:00 nginx: worker process\n",
                "stderr": ""
            }
        elif "error" in command:
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": "command not found: error\n"
            }
        else:
            return {
                "exit_code": 0,
                "stdout": f"Command '{command}' executed successfully\n",
                "stderr": ""
            }


class LXDMockClient:
    """Mock LXD API client for testing."""
    
    def __init__(self, host: str = "192.168.10.101", **kwargs):
        self.host = host
        self.connected = False
        self.authenticated = False
        self.fixtures = LXDAPIFixtures()
    
    async def connect(self) -> bool:
        """Mock connection method."""
        self.connected = True
        return True
    
    async def authenticate(self) -> bool:
        """Mock authentication method."""
        self.authenticated = True
        return True
    
    async def get_server_info(self) -> Dict[str, Any]:
        """Mock server info retrieval."""
        return self.fixtures.server_info()
    
    async def get_containers(self, **filters) -> List[Dict[str, Any]]:
        """Mock container listing with filtering."""
        containers = self.fixtures.containers_list()
        
        # Apply filters
        if 'status' in filters:
            containers = [c for c in containers if c['status'] == filters['status']]
        
        if 'name_pattern' in filters:
            pattern = filters['name_pattern'].replace('*', '')
            containers = [c for c in containers if pattern in c['name']]
        
        if 'image' in filters:
            image_filter = filters['image'].replace('*', '')
            containers = [c for c in containers 
                         if image_filter in c['config'].get('image.os', '') or 
                            image_filter in c['config'].get('image.release', '')]
        
        return containers
    
    async def get_container_details(self, name: str) -> Dict[str, Any]:
        """Mock container details retrieval."""
        containers = self.fixtures.containers_list()
        for container in containers:
            if container['name'] == name:
                return container
        raise Exception(f"Container '{name}' not found")
    
    async def get_container_state(self, name: str) -> Dict[str, Any]:
        """Mock container state retrieval."""
        return self.fixtures.container_state(name)
    
    async def get_images(self, **filters) -> List[Dict[str, Any]]:
        """Mock image listing."""
        images = self.fixtures.images_list()
        
        if 'architecture' in filters:
            images = [i for i in images if i['architecture'] == filters['architecture']]
        
        return images
    
    async def get_networks(self, **filters) -> List[Dict[str, Any]]:
        """Mock network listing."""
        return self.fixtures.networks_list()
    
    async def get_storage_pools(self, **filters) -> List[Dict[str, Any]]:
        """Mock storage pool listing."""
        return self.fixtures.storage_pools_list()
    
    async def get_storage_pool_resources(self, pool_name: str) -> Dict[str, Any]:
        """Mock storage pool resources."""
        return self.fixtures.storage_pool_resources(pool_name)
    
    async def get_cluster_members(self) -> List[Dict[str, Any]]:
        """Mock cluster members listing."""
        return self.fixtures.cluster_members()
    
    async def create_container(self, name: str, **config) -> Dict[str, Any]:
        """Mock container creation."""
        operation_id = f"operation-{name}-create"
        return {
            "success": True,
            "operation_id": operation_id,
            "container_name": name,
            "status": "creating"
        }
    
    async def start_container(self, name: str) -> Dict[str, Any]:
        """Mock container start."""
        return {
            "success": True,
            "container_name": name,
            "status": "running"
        }
    
    async def stop_container(self, name: str, force: bool = False) -> Dict[str, Any]:
        """Mock container stop."""
        return {
            "success": True,
            "container_name": name,
            "status": "stopped",
            "force": force
        }
    
    async def delete_container(self, name: str, force: bool = False) -> Dict[str, Any]:
        """Mock container deletion."""
        return {
            "success": True,
            "container_name": name,
            "deleted": True,
            "force": force
        }
    
    async def exec_container(self, name: str, command: str, **kwargs) -> Dict[str, Any]:
        """Mock command execution in container."""
        return self.fixtures.exec_result(command)
    
    async def get_container_logs(self, name: str, lines: int = 100) -> str:
        """Mock container logs retrieval."""
        logs = self.fixtures.container_logs(name)
        log_lines = logs.split('\n')
        return '\n'.join(log_lines[-lines:]) if lines > 0 else logs
    
    async def get_snapshots(self, container_name: str) -> List[Dict[str, Any]]:
        """Mock snapshot listing."""
        return self.fixtures.container_snapshots(container_name)
    
    async def create_snapshot(self, container_name: str, snapshot_name: str, **config) -> Dict[str, Any]:
        """Mock snapshot creation."""
        return {
            "success": True,
            "container_name": container_name,
            "snapshot_name": snapshot_name,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def restore_snapshot(self, container_name: str, snapshot_name: str) -> Dict[str, Any]:
        """Mock snapshot restoration."""
        return {
            "success": True,
            "container_name": container_name,
            "snapshot_name": snapshot_name,
            "restored_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def upload_file(self, container_name: str, source: str, destination: str, **kwargs) -> Dict[str, Any]:
        """Mock file upload."""
        return {
            "success": True,
            "container_name": container_name,
            "source_path": source,
            "destination_path": destination,
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def download_file(self, container_name: str, source: str, destination: str) -> Dict[str, Any]:
        """Mock file download."""
        return {
            "success": True,
            "container_name": container_name,
            "source_path": source,
            "destination_path": destination,
            "content": b"Mock file content",
            "downloaded_at": datetime.now(timezone.utc).isoformat()
        }


def create_mock_lxd_client(host: str = "192.168.10.101", **kwargs) -> LXDMockClient:
    """Factory function to create mock LXD client."""
    return LXDMockClient(host=host, **kwargs)


def create_async_mock_lxd_client(host: str = "192.168.10.101", **kwargs) -> AsyncMock:
    """Factory function to create AsyncMock LXD client with realistic responses."""
    client = AsyncMock()
    mock_client = LXDMockClient(host=host, **kwargs)
    
    # Configure AsyncMock to return realistic responses
    client.connect = AsyncMock(return_value=True)
    client.authenticate = AsyncMock(return_value=True)
    client.get_server_info = AsyncMock(side_effect=mock_client.get_server_info)
    client.get_containers = AsyncMock(side_effect=mock_client.get_containers)
    client.get_container_details = AsyncMock(side_effect=mock_client.get_container_details)
    client.get_container_state = AsyncMock(side_effect=mock_client.get_container_state)
    client.get_images = AsyncMock(side_effect=mock_client.get_images)
    client.get_networks = AsyncMock(side_effect=mock_client.get_networks)
    client.get_storage_pools = AsyncMock(side_effect=mock_client.get_storage_pools)
    client.get_cluster_members = AsyncMock(side_effect=mock_client.get_cluster_members)
    client.create_container = AsyncMock(side_effect=mock_client.create_container)
    client.start_container = AsyncMock(side_effect=mock_client.start_container)
    client.stop_container = AsyncMock(side_effect=mock_client.stop_container)
    client.delete_container = AsyncMock(side_effect=mock_client.delete_container)
    client.exec_container = AsyncMock(side_effect=mock_client.exec_container)
    client.get_container_logs = AsyncMock(side_effect=mock_client.get_container_logs)
    
    return client


# SSH Mock Fixtures

class SSHMockFixtures:
    """Mock SSH command responses for LXD setup wizard testing."""
    
    @staticmethod
    def lxd_version_check_success() -> Dict[str, Any]:
        """Mock successful LXD version check."""
        return {
            'stdout': 'lxd 5.0.2\n',
            'stderr': '',
            'returncode': 0
        }
    
    @staticmethod
    def lxd_version_check_not_found() -> Dict[str, Any]:
        """Mock LXD not found response."""
        return {
            'stdout': '',
            'stderr': 'command not found: lxd\n',
            'returncode': 127
        }
    
    @staticmethod
    def snap_install_lxd_success() -> Dict[str, Any]:
        """Mock successful snap LXD installation."""
        return {
            'stdout': 'lxd 5.0.2 from Canonical✓ installed\n',
            'stderr': '',
            'returncode': 0
        }
    
    @staticmethod
    def apt_install_lxd_success() -> Dict[str, Any]:
        """Mock successful apt LXD installation."""
        return {
            'stdout': 'Reading package lists...\nThe following packages will be installed:\n  lxd lxd-client\nSetting up lxd...\n',
            'stderr': '',
            'returncode': 0
        }
    
    @staticmethod
    def lxd_init_success() -> Dict[str, Any]:
        """Mock successful LXD initialization."""
        return {
            'stdout': 'Would you like to use LXD clustering? (yes/no) [default=no]: \nDo you want to configure a new storage pool? (yes/no) [default=yes]: \nName of the new storage pool [default=default]: \nName of the storage backend to use (dir, lvm, zfs, btrfs) [default=dir]: \nWould you like to create a new local network bridge? (yes/no) [default=yes]: \nWhat should the new bridge be called? [default=lxdbr0]: \nLXD has been successfully configured.\n',
            'stderr': '',
            'returncode': 0
        }
    
    @staticmethod
    def os_info_ubuntu_22_04() -> Dict[str, Any]:
        """Mock Ubuntu 22.04 OS information."""
        return {
            'stdout': 'NAME="Ubuntu"\nVERSION="22.04.3 LTS (Jammy Jellyfish)"\nID=ubuntu\nID_LIKE=debian\nPRETTY_NAME="Ubuntu 22.04.3 LTS"\nVERSION_ID="22.04"\nHOME_URL="https://www.ubuntu.com/"\nSUPPORT_URL="https://help.ubuntu.com/"\nBUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"\nPRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"\nVERSION_CODENAME=jammy\nUBUNTU_CODENAME=jammy\n',
            'stderr': '',
            'returncode': 0
        }
    
    @staticmethod
    def os_info_debian_11() -> Dict[str, Any]:
        """Mock Debian 11 OS information."""
        return {
            'stdout': 'PRETTY_NAME="Debian GNU/Linux 11 (bullseye)"\nNAME="Debian GNU/Linux"\nVERSION_ID="11"\nVERSION="11 (bullseye)"\nVERSION_CODENAME=bullseye\nID=debian\nHOME_URL="https://www.debian.org/"\nSUPPORT_URL="https://www.debian.org/support"\nBUG_REPORT_URL="https://bugs.debian.org/"\n',
            'stderr': '',
            'returncode': 0
        }


# Export all fixtures and mocks
__all__ = [
    'LXDAPIFixtures',
    'LXDMockClient', 
    'SSHMockFixtures',
    'create_mock_lxd_client',
    'create_async_mock_lxd_client'
]