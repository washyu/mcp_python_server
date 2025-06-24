"""Tests for VM manager module."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.homelab_mcp.vm_manager import (
    deploy_vm_on_platform,
    delete_vm_on_platform,
    list_vms_on_host,
    _deploy_docker_vm,
    _deploy_lxd_vm,
    _delete_docker_vm,
    _delete_lxd_vm,
    _list_docker_vms,
    _list_lxd_vms,
    _auto_discover_vm
)


class MockAsyncSSHConnection:
    """Mock AsyncSSH connection for testing."""
    
    def __init__(self, command_responses=None):
        self.command_responses = command_responses or {}
        self.command_history = []
    
    async def run(self, command, check=True, timeout=None):
        """Mock run method."""
        self.command_history.append(command)
        
        # Create mock result
        result = MagicMock()
        
        # Check for specific command patterns
        if command in self.command_responses:
            response = self.command_responses[command]
            result.exit_status = response.get("exit_status", 0)
            result.stdout = response.get("stdout", "")
            result.stderr = response.get("stderr", "")
        elif "docker ps" in command:
            result.exit_status = 0
            result.stdout = "web-server\tUp 2 hours\t0.0.0.0:8080->80/tcp\napi-server\tUp 1 day\t0.0.0.0:3000->3000/tcp"
        elif "sudo lxc list" in command and "--format json" in command:
            result.exit_status = 0
            result.stdout = json.dumps([
                {
                    "name": "database-server",
                    "status": "Running",
                    "state": {
                        "network": {
                            "eth0": {
                                "addresses": [
                                    {"family": "inet", "address": "192.168.1.101"}
                                ]
                            }
                        }
                    }
                }
            ])
        elif "hostname -I" in command:
            result.exit_status = 0
            result.stdout = "192.168.1.50 "
        elif "|| true" in command:
            result.exit_status = 0
            result.stdout = ""
        else:
            result.exit_status = 0
            result.stdout = ""
        
        result.stderr = result.stderr if hasattr(result, 'stderr') else ""
        return result


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_manager.asyncssh.connect')
async def test_deploy_vm_on_platform_docker(mock_connect):
    """Test deploying Docker VM."""
    # Mock SSH connection
    mock_conn = MockAsyncSSHConnection()
    mock_connect.return_value.__aenter__.return_value = mock_conn
    
    result_json = await deploy_vm_on_platform(
        platform="docker",
        vm_name="test-docker-vm",
        target_host="192.168.1.50",
        ssh_user="admin",
        ssh_password="password123",
        vm_config={"ssh_port": 2222}
    )
    
    result = json.loads(result_json)
    assert result["status"] == "success"
    assert result["platform"] == "docker"
    assert result["name"] == "test-docker-vm"
    assert result["port"] == 2222
    assert "ssh homelab@" in result["ssh_command"]
    
    # Check that Docker commands were executed
    commands = mock_conn.command_history
    docker_run_command = next((cmd for cmd in commands if "docker run" in cmd), None)
    assert docker_run_command is not None
    assert "test-docker-vm" in docker_run_command
    assert "-p 2222:22" in docker_run_command


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_manager.asyncssh.connect')
async def test_deploy_vm_on_platform_lxd(mock_connect):
    """Test deploying LXD VM."""
    # Mock SSH connection with LXD responses
    lxd_responses = {
        "sudo lxc launch ubuntu:22.04 test-lxd-vm": {
            "exit_status": 0,
            "stdout": "Creating test-lxd-vm"
        },
        "sudo lxc list test-lxd-vm --format json": {
            "exit_status": 0,
            "stdout": json.dumps([{
                "name": "test-lxd-vm",
                "status": "Running",
                "state": {
                    "network": {
                        "eth0": {
                            "addresses": [
                                {"family": "inet", "address": "192.168.1.102"}
                            ]
                        }
                    }
                }
            }])
        }
    }
    
    mock_conn = MockAsyncSSHConnection(lxd_responses)
    mock_connect.return_value.__aenter__.return_value = mock_conn
    
    result_json = await deploy_vm_on_platform(
        platform="lxd",
        vm_name="test-lxd-vm",
        target_host="192.168.1.50",
        ssh_user="admin",
        ssh_password="password123"
    )
    
    result = json.loads(result_json)
    assert result["status"] == "success"
    assert result["platform"] == "lxd"
    assert result["name"] == "test-lxd-vm"
    assert result["ip"] == "192.168.1.102"
    assert result["port"] == 22
    
    # Check that LXD commands were executed
    commands = mock_conn.command_history
    lxd_launch_command = next((cmd for cmd in commands if "lxc launch" in cmd), None)
    assert lxd_launch_command is not None
    assert "test-lxd-vm" in lxd_launch_command


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_manager.asyncssh.connect')
async def test_deploy_vm_unsupported_platform(mock_connect):
    """Test deploying VM on unsupported platform."""
    mock_conn = MockAsyncSSHConnection()
    mock_connect.return_value.__aenter__.return_value = mock_conn
    
    result_json = await deploy_vm_on_platform(
        platform="kubernetes",  # Unsupported platform
        vm_name="test-vm",
        target_host="192.168.1.50",
        ssh_user="admin",
        ssh_password="password123"
    )
    
    result = json.loads(result_json)
    assert result["status"] == "error"
    assert "Unsupported platform: kubernetes" in result["message"]


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_manager.asyncssh.connect')
async def test_delete_vm_on_platform_docker(mock_connect):
    """Test deleting Docker VM."""
    mock_conn = MockAsyncSSHConnection({
        "docker stop test-vm": {"exit_status": 0},
        "docker rm test-vm": {"exit_status": 0}
    })
    mock_connect.return_value.__aenter__.return_value = mock_conn
    
    result_json = await delete_vm_on_platform(
        platform="docker",
        vm_name="test-vm",
        target_host="192.168.1.50",
        ssh_user="admin",
        ssh_password="password123"
    )
    
    result = json.loads(result_json)
    assert result["status"] == "success"
    assert "deleted successfully" in result["message"]
    assert "test-vm" in result["message"]
    
    # Check that Docker commands were executed
    commands = mock_conn.command_history
    assert "docker stop test-vm" in commands
    assert "docker rm test-vm" in commands


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_manager.asyncssh.connect')
async def test_delete_vm_on_platform_lxd(mock_connect):
    """Test deleting LXD VM."""
    mock_conn = MockAsyncSSHConnection({
        "sudo lxc stop test-vm --force": {"exit_status": 0},
        "sudo lxc delete test-vm": {"exit_status": 0}
    })
    mock_connect.return_value.__aenter__.return_value = mock_conn
    
    result_json = await delete_vm_on_platform(
        platform="lxd",
        vm_name="test-vm",
        target_host="192.168.1.50",
        ssh_user="admin",
        ssh_password="password123"
    )
    
    result = json.loads(result_json)
    assert result["status"] == "success"
    assert "deleted successfully" in result["message"]
    assert "test-vm" in result["message"]
    
    # Check that LXD commands were executed
    commands = mock_conn.command_history
    assert "sudo lxc stop test-vm --force" in commands
    assert "sudo lxc delete test-vm" in commands


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_manager.asyncssh.connect')
async def test_list_vms_on_host(mock_connect):
    """Test listing VMs on host."""
    mock_conn = MockAsyncSSHConnection()
    mock_connect.return_value.__aenter__.return_value = mock_conn
    
    result_json = await list_vms_on_host(
        target_host="192.168.1.50",
        ssh_user="admin",
        ssh_password="password123",
        platforms=["docker", "lxd"]
    )
    
    result = json.loads(result_json)
    assert result["status"] == "success"
    assert result["host"] == "192.168.1.50"
    assert result["total_vms"] == 3  # 2 Docker + 1 LXD from mock responses
    
    # Check VM details
    vms = result["vms"]
    docker_vms = [vm for vm in vms if vm["platform"] == "docker"]
    lxd_vms = [vm for vm in vms if vm["platform"] == "lxd"]
    
    assert len(docker_vms) == 2
    assert len(lxd_vms) == 1
    
    # Check Docker VM details
    assert docker_vms[0]["name"] == "web-server"
    assert docker_vms[0]["status"] == "Up 2 hours"
    assert docker_vms[1]["name"] == "api-server"
    
    # Check LXD VM details
    assert lxd_vms[0]["name"] == "database-server"
    assert lxd_vms[0]["status"] == "Running"
    assert lxd_vms[0]["ip"] == "192.168.1.101"


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_manager.asyncssh.connect')
async def test_deploy_vm_connection_error(mock_connect):
    """Test VM deployment with connection error."""
    # Mock connection error
    mock_connect.side_effect = Exception("Connection failed")
    
    result_json = await deploy_vm_on_platform(
        platform="docker",
        vm_name="test-vm",
        target_host="192.168.1.50",
        ssh_user="admin",
        ssh_password="wrong-password"
    )
    
    result = json.loads(result_json)
    assert result["status"] == "error"
    assert "Connection failed" in result["message"]


@pytest.mark.asyncio
async def test_deploy_docker_vm():
    """Test _deploy_docker_vm function directly."""
    mock_conn = MockAsyncSSHConnection()
    
    result = await _deploy_docker_vm(mock_conn, "test-docker", 2222)
    
    assert result["status"] == "success"
    assert result["platform"] == "docker"
    assert result["name"] == "test-docker"
    assert result["port"] == 2222
    
    # Check commands were executed
    commands = mock_conn.command_history
    assert any("docker run" in cmd for cmd in commands)
    assert any("apt update" in cmd for cmd in commands)
    assert any("openssh-server" in cmd for cmd in commands)


@pytest.mark.asyncio
async def test_deploy_lxd_vm():
    """Test _deploy_lxd_vm function directly."""
    lxd_responses = {
        "sudo lxc launch ubuntu:22.04 test-lxd": {
            "exit_status": 0,
            "stdout": "Creating test-lxd"
        },
        "sudo lxc list test-lxd --format json": {
            "exit_status": 0,
            "stdout": json.dumps([{
                "name": "test-lxd",
                "status": "Running",
                "state": {
                    "network": {
                        "eth0": {
                            "addresses": [
                                {"family": "inet", "address": "192.168.1.200"}
                            ]
                        }
                    }
                }
            }])
        }
    }
    
    mock_conn = MockAsyncSSHConnection(lxd_responses)
    
    result = await _deploy_lxd_vm(mock_conn, "test-lxd")
    
    assert result["status"] == "success"
    assert result["platform"] == "lxd"
    assert result["name"] == "test-lxd"
    assert result["ip"] == "192.168.1.200"
    assert result["port"] == 22


@pytest.mark.asyncio
async def test_list_docker_vms():
    """Test _list_docker_vms function directly."""
    mock_conn = MockAsyncSSHConnection()
    
    vms = await _list_docker_vms(mock_conn)
    
    assert len(vms) == 2
    assert vms[0]["platform"] == "docker"
    assert vms[0]["name"] == "web-server"
    assert vms[0]["status"] == "Up 2 hours"
    assert vms[1]["name"] == "api-server"


@pytest.mark.asyncio
async def test_list_lxd_vms():
    """Test _list_lxd_vms function directly."""
    mock_conn = MockAsyncSSHConnection()
    
    vms = await _list_lxd_vms(mock_conn)
    
    assert len(vms) == 1
    assert vms[0]["platform"] == "lxd"
    assert vms[0]["name"] == "database-server"
    assert vms[0]["status"] == "Running"
    assert vms[0]["ip"] == "192.168.1.101"


@pytest.mark.asyncio
async def test_delete_docker_vm():
    """Test _delete_docker_vm function directly."""
    mock_conn = MockAsyncSSHConnection({
        "docker stop test-vm": {"exit_status": 0},
        "docker rm test-vm": {"exit_status": 0}
    })
    
    result = await _delete_docker_vm(mock_conn, "test-vm")
    
    assert result["status"] == "success"
    assert "deleted successfully" in result["message"]


@pytest.mark.asyncio
async def test_delete_lxd_vm():
    """Test _delete_lxd_vm function directly."""
    mock_conn = MockAsyncSSHConnection({
        "sudo lxc stop test-vm --force": {"exit_status": 0},
        "sudo lxc delete test-vm": {"exit_status": 0}
    })
    
    result = await _delete_lxd_vm(mock_conn, "test-vm")
    
    assert result["status"] == "success"
    assert "deleted successfully" in result["message"]


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_manager.ssh_discover_system')
@patch('src.homelab_mcp.vm_manager.NetworkSiteMap')
async def test_auto_discover_vm(mock_sitemap_class, mock_ssh_discover):
    """Test automatic VM discovery and cataloging."""
    # Mock sitemap
    mock_sitemap = MagicMock()
    mock_sitemap.parse_discovery_output.return_value = {"hostname": "test-vm"}
    mock_sitemap.store_device.return_value = 123
    mock_sitemap_class.return_value = mock_sitemap
    
    # Mock SSH discovery
    mock_ssh_discover.return_value = json.dumps({
        "status": "success",
        "hostname": "test-vm",
        "data": {"cpu": {"cores": "2"}}
    })
    
    vm_info = {
        "ip": "192.168.1.100",
        "port": 22,
        "name": "test-vm"
    }
    
    device_id = await _auto_discover_vm(vm_info, "192.168.1.50")
    
    assert device_id == 123
    mock_ssh_discover.assert_called_once_with(
        hostname="192.168.1.100",
        username="homelab",
        password="homelab123",
        port=22
    )
    mock_sitemap.store_device.assert_called_once()


@pytest.mark.asyncio
async def test_auto_discover_vm_no_ip():
    """Test auto-discovery with no IP address."""
    vm_info = {"name": "test-vm"}  # No IP
    
    device_id = await _auto_discover_vm(vm_info, "192.168.1.50")
    
    assert device_id is None


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_manager.ssh_discover_system')
async def test_auto_discover_vm_discovery_fails(mock_ssh_discover):
    """Test auto-discovery when SSH discovery fails."""
    # Mock SSH discovery failure
    mock_ssh_discover.return_value = json.dumps({
        "status": "error",
        "message": "Connection failed"
    })
    
    vm_info = {
        "ip": "192.168.1.100",
        "port": 22,
        "name": "test-vm"
    }
    
    device_id = await _auto_discover_vm(vm_info, "192.168.1.50")
    
    assert device_id is None