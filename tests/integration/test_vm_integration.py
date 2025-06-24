"""Integration tests for VM management functionality."""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_manager.asyncssh.connect')
@patch('src.homelab_mcp.vm_manager.ssh_discover_system')
@patch('src.homelab_mcp.vm_manager.NetworkSiteMap')
async def test_full_vm_lifecycle_docker(mock_sitemap_class, mock_ssh_discover, mock_connect):
    """Test complete VM lifecycle: deploy -> list -> discover -> delete."""
    from src.homelab_mcp.tools import execute_tool
    
    # Mock sitemap for auto-discovery
    mock_sitemap = MagicMock()
    mock_sitemap.parse_discovery_output.return_value = {"hostname": "integration-test-vm"}
    mock_sitemap.store_device.return_value = 456
    mock_sitemap_class.return_value = mock_sitemap
    
    # Mock SSH discovery for auto-cataloging
    mock_ssh_discover.return_value = json.dumps({
        "status": "success",
        "hostname": "integration-test-vm",
        "data": {
            "cpu": {"model": "Test CPU", "cores": "2"},
            "memory": {"total": "4G", "used": "2G"}
        }
    })
    
    # Mock SSH connection responses
    command_responses = {
        "docker stop integration-test-vm || true": {"exit_status": 0},
        "docker rm integration-test-vm || true": {"exit_status": 0},
        "hostname -I | awk '{print $1}'": {"exit_status": 0, "stdout": "192.168.1.50"},
        "docker ps -a --format \"{{.Names}}\t{{.Status}}\t{{.Ports}}\"": {
            "exit_status": 0,
            "stdout": "integration-test-vm\tUp 1 minute\t0.0.0.0:2333->22/tcp"
        },
        "docker stop integration-test-vm": {"exit_status": 0},
        "docker rm integration-test-vm": {"exit_status": 0}
    }
    
    class MockConnection:
        def __init__(self):
            self.command_history = []
        
        async def run(self, command, check=True, timeout=None):
            self.command_history.append(command)
            result = MagicMock()
            
            if command in command_responses:
                response = command_responses[command]
                result.exit_status = response.get("exit_status", 0)
                result.stdout = response.get("stdout", "")
                result.stderr = response.get("stderr", "")
            else:
                result.exit_status = 0
                result.stdout = ""
                result.stderr = ""
            
            return result
    
    mock_conn = MockConnection()
    mock_connect.return_value.__aenter__.return_value = mock_conn
    
    # Step 1: Deploy a Docker VM
    print("Step 1: Deploying Docker VM...")
    deploy_result = await execute_tool("deploy_vm", {
        "platform": "docker",
        "vm_name": "integration-test-vm",
        "target_host": "192.168.1.50",
        "ssh_user": "admin",
        "ssh_password": "password123",
        "vm_config": {
            "cpu_cores": 2,
            "memory_gb": 4,
            "ssh_port": 2333
        }
    })
    
    deploy_data = json.loads(deploy_result["content"][0]["text"])
    assert deploy_data["status"] == "success"
    assert deploy_data["platform"] == "docker"
    assert deploy_data["name"] == "integration-test-vm"
    assert deploy_data["port"] == 2333
    
    # Verify auto-discovery was triggered
    mock_ssh_discover.assert_called_once_with(
        hostname="192.168.1.50",
        username="homelab",
        password="homelab123",
        port=2333
    )
    mock_sitemap.store_device.assert_called_once()
    
    # Step 2: List VMs to verify deployment
    print("Step 2: Listing VMs...")
    list_result = await execute_tool("list_vms", {
        "target_host": "192.168.1.50",
        "ssh_user": "admin",
        "ssh_password": "password123",
        "platforms": ["docker"]
    })
    
    list_data = json.loads(list_result["content"][0]["text"])
    assert list_data["status"] == "success"
    assert list_data["total_vms"] == 1
    assert list_data["vms"][0]["name"] == "integration-test-vm"
    assert list_data["vms"][0]["platform"] == "docker"
    assert "Up 1 minute" in list_data["vms"][0]["status"]
    
    # Step 3: Delete the VM
    print("Step 3: Deleting VM...")
    delete_result = await execute_tool("delete_vm", {
        "platform": "docker",
        "vm_name": "integration-test-vm",
        "target_host": "192.168.1.50",
        "ssh_user": "admin",
        "ssh_password": "password123"
    })
    
    delete_data = json.loads(delete_result["content"][0]["text"])
    assert delete_data["status"] == "success"
    assert "deleted successfully" in delete_data["message"]
    assert "integration-test-vm" in delete_data["message"]
    
    # Verify commands were executed in correct order
    commands = mock_conn.command_history
    assert any("docker run" in cmd and "integration-test-vm" in cmd for cmd in commands)
    assert any("docker stop integration-test-vm" in cmd for cmd in commands)
    assert any("docker rm integration-test-vm" in cmd for cmd in commands)
    
    print("✅ Full VM lifecycle test completed successfully!")


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_manager.asyncssh.connect')
async def test_platform_agnostic_deployment(mock_connect):
    """Test deploying VMs on multiple platforms with same interface."""
    from src.homelab_mcp.tools import execute_tool
    
    # Mock responses for different platforms
    platform_responses = {
        "docker": {
            "hostname -I | awk '{print $1}'": {"exit_status": 0, "stdout": "192.168.1.50"}
        },
        "lxd": {
            "sudo lxc launch ubuntu:22.04 test-multi-platform": {"exit_status": 0},
            "sudo lxc list test-multi-platform --format json": {
                "exit_status": 0,
                "stdout": json.dumps([{
                    "name": "test-multi-platform",
                    "status": "Running",
                    "state": {
                        "network": {
                            "eth0": {
                                "addresses": [
                                    {"family": "inet", "address": "192.168.1.201"}
                                ]
                            }
                        }
                    }
                }])
            }
        }
    }
    
    class MockConnection:
        def __init__(self, platform):
            self.platform = platform
            self.command_history = []
        
        async def run(self, command, check=True, timeout=None):
            self.command_history.append(command)
            result = MagicMock()
            
            responses = platform_responses.get(self.platform, {})
            if command in responses:
                response = responses[command]
                result.exit_status = response.get("exit_status", 0)
                result.stdout = response.get("stdout", "")
                result.stderr = response.get("stderr", "")
            else:
                result.exit_status = 0
                result.stdout = ""
                result.stderr = ""
            
            return result
    
    # Test Docker deployment
    mock_connect.return_value.__aenter__.return_value = MockConnection("docker")
    
    docker_result = await execute_tool("deploy_vm", {
        "platform": "docker",
        "vm_name": "test-multi-platform",
        "target_host": "192.168.1.50",
        "ssh_user": "admin",
        "ssh_password": "password123"
    })
    
    docker_data = json.loads(docker_result["content"][0]["text"])
    assert docker_data["status"] == "success"
    assert docker_data["platform"] == "docker"
    
    # Test LXD deployment
    mock_connect.return_value.__aenter__.return_value = MockConnection("lxd")
    
    lxd_result = await execute_tool("deploy_vm", {
        "platform": "lxd",
        "vm_name": "test-multi-platform",
        "target_host": "192.168.1.50",
        "ssh_user": "admin",
        "ssh_password": "password123"
    })
    
    lxd_data = json.loads(lxd_result["content"][0]["text"])
    assert lxd_data["status"] == "success"
    assert lxd_data["platform"] == "lxd"
    assert lxd_data["ip"] == "192.168.1.201"
    
    print("✅ Platform-agnostic deployment test completed!")


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_manager.asyncssh.connect')
async def test_error_handling_integration(mock_connect):
    """Test error handling across the VM management workflow."""
    from src.homelab_mcp.tools import execute_tool
    
    # Mock connection failure
    mock_connect.side_effect = Exception("SSH connection failed")
    
    # Test deploy_vm error handling
    deploy_result = await execute_tool("deploy_vm", {
        "platform": "docker",
        "vm_name": "failing-vm",
        "target_host": "192.168.1.99",  # Non-existent host
        "ssh_user": "admin",
        "ssh_password": "password123"
    })
    
    deploy_data = json.loads(deploy_result["content"][0]["text"])
    assert deploy_data["status"] == "error"
    assert "SSH connection failed" in deploy_data["message"]
    
    # Test list_vms error handling
    list_result = await execute_tool("list_vms", {
        "target_host": "192.168.1.99",
        "ssh_user": "admin",
        "ssh_password": "password123"
    })
    
    list_data = json.loads(list_result["content"][0]["text"])
    assert list_data["status"] == "error"
    assert "SSH connection failed" in list_data["message"]
    
    # Test delete_vm error handling
    delete_result = await execute_tool("delete_vm", {
        "platform": "docker",
        "vm_name": "non-existent-vm",
        "target_host": "192.168.1.99",
        "ssh_user": "admin",
        "ssh_password": "password123"
    })
    
    delete_data = json.loads(delete_result["content"][0]["text"])
    assert delete_data["status"] == "error"
    assert "SSH connection failed" in delete_data["message"]
    
    print("✅ Error handling integration test completed!")


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_manager.asyncssh.connect')
async def test_vm_configuration_variations(mock_connect):
    """Test different VM configuration options."""
    from src.homelab_mcp.tools import execute_tool
    
    class MockConnection:
        def __init__(self):
            self.command_history = []
        
        async def run(self, command, check=True, timeout=None):
            self.command_history.append(command)
            result = MagicMock()
            result.exit_status = 0
            result.stdout = "192.168.1.50"
            result.stderr = ""
            return result
    
    mock_conn = MockConnection()
    mock_connect.return_value.__aenter__.return_value = mock_conn
    
    # Test with custom configuration
    result = await execute_tool("deploy_vm", {
        "platform": "docker",
        "vm_name": "custom-config-vm",
        "target_host": "192.168.1.50",
        "ssh_user": "admin",
        "ssh_password": "password123",
        "vm_config": {
            "cpu_cores": 4,
            "memory_gb": 8,
            "ssh_port": 2555
        }
    })
    
    data = json.loads(result["content"][0]["text"])
    assert data["status"] == "success"
    assert data["port"] == 2555
    
    # Verify custom port was used in Docker command
    commands = mock_conn.command_history
    docker_run_cmd = next((cmd for cmd in commands if "docker run" in cmd), None)
    assert docker_run_cmd is not None
    assert "-p 2555:22" in docker_run_cmd
    
    print("✅ VM configuration variations test completed!")


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_manager.asyncssh.connect')
async def test_list_multiple_platforms(mock_connect):
    """Test listing VMs across multiple platforms simultaneously."""
    from src.homelab_mcp.tools import execute_tool
    
    class MockConnection:
        def __init__(self):
            self.command_history = []
        
        async def run(self, command, check=True, timeout=None):
            self.command_history.append(command)
            result = MagicMock()
            result.exit_status = 0
            
            if "docker ps" in command:
                result.stdout = "docker-vm1\tUp 1 hour\t0.0.0.0:2222->22/tcp\ndocker-vm2\tUp 2 hours\t0.0.0.0:2223->22/tcp"
            elif "sudo lxc list" in command and "--format json" in command:
                result.stdout = json.dumps([
                    {
                        "name": "lxd-vm1",
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
                    },
                    {
                        "name": "lxd-vm2",
                        "status": "Stopped",
                        "state": {
                            "network": {}
                        }
                    }
                ])
            else:
                result.stdout = ""
            
            result.stderr = ""
            return result
    
    mock_conn = MockConnection()
    mock_connect.return_value.__aenter__.return_value = mock_conn
    
    result = await execute_tool("list_vms", {
        "target_host": "192.168.1.50",
        "ssh_user": "admin",
        "ssh_password": "password123",
        "platforms": ["docker", "lxd"]
    })
    
    data = json.loads(result["content"][0]["text"])
    assert data["status"] == "success"
    assert data["total_vms"] == 4  # 2 Docker + 2 LXD
    
    # Verify VM distribution
    vms = data["vms"]
    docker_vms = [vm for vm in vms if vm["platform"] == "docker"]
    lxd_vms = [vm for vm in vms if vm["platform"] == "lxd"]
    
    assert len(docker_vms) == 2
    assert len(lxd_vms) == 2
    
    # Check specific VM details
    assert any(vm["name"] == "docker-vm1" for vm in docker_vms)
    assert any(vm["name"] == "lxd-vm1" for vm in lxd_vms)
    assert any(vm["status"] == "Running" for vm in lxd_vms)
    assert any(vm["status"] == "Stopped" for vm in lxd_vms)
    
    print("✅ Multi-platform listing test completed!")


if __name__ == "__main__":
    # Run a simple test if executed directly
    import asyncio
    
    async def run_simple_test():
        print("Running VM management integration tests...")
        # This would normally be run via pytest
        print("Use 'pytest tests/integration/test_vm_integration.py' to run these tests")
    
    asyncio.run(run_simple_test())