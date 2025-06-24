"""Tests for MCP tools."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.homelab_mcp.tools import get_available_tools, execute_tool


def test_get_available_tools():
    """Test getting available tools."""
    tools = get_available_tools()
    
    assert len(tools) == 17  # Original 4 + 6 sitemap tools + 3 VM management tools + 4 VM operational tools
    assert "hello_world" in tools
    assert "ssh_discover" in tools
    assert "setup_mcp_admin" in tools
    assert "verify_mcp_admin" in tools
    
    # New sitemap tools
    assert "discover_and_map" in tools
    assert "bulk_discover_and_map" in tools
    assert "get_network_sitemap" in tools
    assert "analyze_network_topology" in tools
    assert "suggest_deployments" in tools
    assert "get_device_changes" in tools
    
    # New VM management tools
    assert "deploy_vm" in tools
    assert "delete_vm" in tools
    assert "list_vms" in tools
    
    # New VM operational tools
    assert "control_vm" in tools
    assert "get_vm_status" in tools
    assert "get_vm_logs" in tools
    assert "manage_vm_services" in tools
    
    # Check hello_world tool schema
    hello_tool = tools["hello_world"]
    assert "description" in hello_tool
    assert "inputSchema" in hello_tool
    
    # Check ssh_discover tool schema
    ssh_tool = tools["ssh_discover"]
    assert "description" in ssh_tool
    assert "inputSchema" in ssh_tool
    assert "hostname" in ssh_tool["inputSchema"]["properties"]
    assert "username" in ssh_tool["inputSchema"]["properties"]


@pytest.mark.asyncio
async def test_execute_hello_world():
    """Test executing hello_world tool."""
    result = await execute_tool("hello_world", {})
    
    assert "content" in result
    assert len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"
    assert "Hello" in result["content"][0]["text"]


@pytest.mark.asyncio
async def test_execute_unknown_tool():
    """Test executing unknown tool raises error."""
    with pytest.raises(ValueError, match="Unknown tool"):
        await execute_tool("nonexistent_tool", {})


@pytest.mark.asyncio
@patch('src.homelab_mcp.tools.ssh_discover_system')
async def test_execute_ssh_discover(mock_ssh_discover):
    """Test executing ssh_discover tool."""
    # Mock the SSH discovery response
    mock_response = json.dumps({
        "status": "success",
        "hostname": "test-host",
        "data": {
            "cpu": {"model": "Test CPU", "cores": "4"},
            "memory": {"total": "8G", "used": "4G"}
        }
    }, indent=2)
    mock_ssh_discover.return_value = mock_response
    
    result = await execute_tool("ssh_discover", {
        "hostname": "test-host",
        "username": "test-user",
        "password": "test-pass"
    })
    
    assert "content" in result
    assert len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"
    
    # Verify the SSH function was called with correct arguments
    mock_ssh_discover.assert_called_once_with(
        hostname="test-host",
        username="test-user", 
        password="test-pass"
    )


@pytest.mark.asyncio
@patch('src.homelab_mcp.tools.discover_and_store')
async def test_execute_discover_and_map(mock_discover_and_store):
    """Test executing discover_and_map tool."""
    # Mock the discover and store response
    mock_response = json.dumps({
        "status": "success",
        "device_id": 1,
        "hostname": "test-server",
        "discovery_status": "success"
    })
    mock_discover_and_store.return_value = mock_response
    
    result = await execute_tool("discover_and_map", {
        "hostname": "test-host",
        "username": "test-user",
        "password": "test-pass"
    })
    
    assert "content" in result
    assert len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"
    
    # Verify the function was called
    mock_discover_and_store.assert_called_once()


@pytest.mark.asyncio
@patch('src.homelab_mcp.tools.bulk_discover_and_store')
async def test_execute_bulk_discover_and_map(mock_bulk_discover):
    """Test executing bulk_discover_and_map tool."""
    # Mock the bulk discovery response
    mock_response = json.dumps({
        "status": "success",
        "total_targets": 2,
        "results": [
            {"status": "success", "hostname": "host1"},
            {"status": "success", "hostname": "host2"}
        ]
    })
    mock_bulk_discover.return_value = mock_response
    
    targets = [
        {"hostname": "host1", "username": "user1"},
        {"hostname": "host2", "username": "user2"}
    ]
    
    result = await execute_tool("bulk_discover_and_map", {"targets": targets})
    
    assert "content" in result
    assert len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"
    
    # Verify the function was called with targets
    mock_bulk_discover.assert_called_once_with(mock_bulk_discover.call_args[0][0], targets)


@pytest.mark.asyncio
@patch('src.homelab_mcp.tools.NetworkSiteMap')
async def test_execute_get_network_sitemap(mock_sitemap_class):
    """Test executing get_network_sitemap tool."""
    # Mock the sitemap instance and its methods
    mock_sitemap = MagicMock()
    mock_sitemap.get_all_devices.return_value = [
        {"id": 1, "hostname": "test-server", "status": "success"},
        {"id": 2, "hostname": "test-server2", "status": "error"}
    ]
    mock_sitemap_class.return_value = mock_sitemap
    
    result = await execute_tool("get_network_sitemap", {})
    
    assert "content" in result
    assert len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"
    
    # Parse the JSON response
    response_data = json.loads(result["content"][0]["text"])
    assert response_data["status"] == "success"
    assert response_data["total_devices"] == 2
    assert len(response_data["devices"]) == 2


@pytest.mark.asyncio
@patch('src.homelab_mcp.tools.NetworkSiteMap')
async def test_execute_analyze_network_topology(mock_sitemap_class):
    """Test executing analyze_network_topology tool."""
    # Mock the sitemap instance and its methods
    mock_sitemap = MagicMock()
    mock_sitemap.analyze_network_topology.return_value = {
        "total_devices": 3,
        "online_devices": 2,
        "offline_devices": 1,
        "operating_systems": {"Ubuntu 22.04": 2},
        "network_segments": {"192.168.1.0/24": 3}
    }
    mock_sitemap_class.return_value = mock_sitemap
    
    result = await execute_tool("analyze_network_topology", {})
    
    assert "content" in result
    assert len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"
    
    # Parse the JSON response
    response_data = json.loads(result["content"][0]["text"])
    assert response_data["status"] == "success"
    assert "analysis" in response_data
    assert response_data["analysis"]["total_devices"] == 3


@pytest.mark.asyncio
@patch('src.homelab_mcp.tools.NetworkSiteMap')
async def test_execute_suggest_deployments(mock_sitemap_class):
    """Test executing suggest_deployments tool."""
    # Mock the sitemap instance and its methods
    mock_sitemap = MagicMock()
    mock_sitemap.suggest_deployments.return_value = {
        "load_balancer_candidates": [
            {"hostname": "high-spec-server", "reason": "8 cores, 16G RAM"}
        ],
        "database_candidates": [
            {"hostname": "storage-server", "reason": "Low disk usage (20%), 32G RAM"}
        ],
        "monitoring_targets": [
            {"hostname": "server1", "connection_ip": "192.168.1.10"}
        ],
        "upgrade_recommendations": []
    }
    mock_sitemap_class.return_value = mock_sitemap
    
    result = await execute_tool("suggest_deployments", {})
    
    assert "content" in result
    assert len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"
    
    # Parse the JSON response
    response_data = json.loads(result["content"][0]["text"])
    assert response_data["status"] == "success"
    assert "suggestions" in response_data
    assert len(response_data["suggestions"]["load_balancer_candidates"]) == 1


@pytest.mark.asyncio
@patch('src.homelab_mcp.tools.NetworkSiteMap')
async def test_execute_get_device_changes(mock_sitemap_class):
    """Test executing get_device_changes tool."""
    # Mock the sitemap instance and its methods
    mock_sitemap = MagicMock()
    mock_sitemap.get_device_changes.return_value = [
        {
            "data": {"hostname": "test-server", "status": "success"},
            "discovered_at": "2024-01-01T12:00:00"
        },
        {
            "data": {"hostname": "test-server", "status": "success"},
            "discovered_at": "2024-01-01T11:00:00"
        }
    ]
    mock_sitemap_class.return_value = mock_sitemap
    
    result = await execute_tool("get_device_changes", {"device_id": 1, "limit": 5})
    
    assert "content" in result
    assert len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"
    
    # Parse the JSON response
    response_data = json.loads(result["content"][0]["text"])
    assert response_data["status"] == "success"
    assert response_data["device_id"] == 1
    assert len(response_data["changes"]) == 2


def test_sitemap_tool_schemas():
    """Test that all sitemap tools have proper schemas."""
    tools = get_available_tools()
    
    # Test discover_and_map schema
    discover_tool = tools["discover_and_map"]
    assert "description" in discover_tool
    assert "inputSchema" in discover_tool
    assert "hostname" in discover_tool["inputSchema"]["properties"]
    assert "username" in discover_tool["inputSchema"]["properties"]
    assert discover_tool["inputSchema"]["required"] == ["hostname", "username"]
    
    # Test bulk_discover_and_map schema
    bulk_tool = tools["bulk_discover_and_map"]
    assert "targets" in bulk_tool["inputSchema"]["properties"]
    assert bulk_tool["inputSchema"]["properties"]["targets"]["type"] == "array"
    
    # Test get_device_changes schema
    changes_tool = tools["get_device_changes"]
    assert "device_id" in changes_tool["inputSchema"]["properties"]
    assert changes_tool["inputSchema"]["required"] == ["device_id"]
    
    # Test tools with no required parameters
    for tool_name in ["get_network_sitemap", "analyze_network_topology", "suggest_deployments"]:
        tool = tools[tool_name]
        assert tool["inputSchema"]["required"] == []


def test_vm_management_tool_schemas():
    """Test that VM management tools have proper schemas."""
    tools = get_available_tools()
    
    # Test deploy_vm schema
    deploy_tool = tools["deploy_vm"]
    assert "description" in deploy_tool
    assert "Deploy a VM/container on a specified platform" in deploy_tool["description"]
    assert "inputSchema" in deploy_tool
    assert "platform" in deploy_tool["inputSchema"]["properties"]
    assert "target_host" in deploy_tool["inputSchema"]["properties"]
    assert "ssh_user" in deploy_tool["inputSchema"]["properties"]
    assert "ssh_password" in deploy_tool["inputSchema"]["properties"]
    assert "vm_config" in deploy_tool["inputSchema"]["properties"]
    assert deploy_tool["inputSchema"]["required"] == ["platform", "target_host", "ssh_user", "ssh_password"]
    
    # Check platform enum
    platform_enum = deploy_tool["inputSchema"]["properties"]["platform"]["enum"]
    assert "docker" in platform_enum
    assert "lxd" in platform_enum
    assert "proxmox" in platform_enum
    
    # Test delete_vm schema
    delete_tool = tools["delete_vm"]
    assert "description" in delete_tool
    assert "Delete/destroy a VM/container" in delete_tool["description"]
    assert "platform" in delete_tool["inputSchema"]["properties"]
    assert "vm_name" in delete_tool["inputSchema"]["properties"]
    assert delete_tool["inputSchema"]["required"] == ["platform", "vm_name", "target_host", "ssh_user", "ssh_password"]
    
    # Test list_vms schema
    list_tool = tools["list_vms"]
    assert "description" in list_tool
    assert "List all VMs/containers" in list_tool["description"]
    assert "target_host" in list_tool["inputSchema"]["properties"]
    assert "platforms" in list_tool["inputSchema"]["properties"]
    assert list_tool["inputSchema"]["properties"]["platforms"]["type"] == "array"
    assert list_tool["inputSchema"]["required"] == ["target_host", "ssh_user", "ssh_password"]


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_manager.deploy_vm_on_platform')
async def test_execute_deploy_vm(mock_deploy_vm):
    """Test executing deploy_vm tool."""
    # Mock the VM deployment response
    mock_response = json.dumps({
        "status": "success",
        "platform": "docker",
        "name": "test-vm",
        "ip": "192.168.1.100",
        "port": 2222,
        "ssh_command": "ssh homelab@192.168.1.100 -p 2222",
        "credentials": "homelab:homelab123"
    })
    mock_deploy_vm.return_value = mock_response
    
    result = await execute_tool("deploy_vm", {
        "platform": "docker",
        "vm_name": "test-vm",
        "target_host": "192.168.1.50",
        "ssh_user": "admin",
        "ssh_password": "password123",
        "vm_config": {
            "cpu_cores": 2,
            "memory_gb": 4,
            "ssh_port": 2222
        }
    })
    
    assert "content" in result
    assert len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"
    
    # Parse the JSON response
    response_data = json.loads(result["content"][0]["text"])
    assert response_data["status"] == "success"
    assert response_data["platform"] == "docker"
    assert response_data["name"] == "test-vm"
    
    # Verify the function was called with correct arguments
    mock_deploy_vm.assert_called_once_with(
        platform="docker",
        vm_name="test-vm",
        target_host="192.168.1.50",
        ssh_user="admin",
        ssh_password="password123",
        vm_config={
            "cpu_cores": 2,
            "memory_gb": 4,
            "ssh_port": 2222
        }
    )


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_manager.delete_vm_on_platform')
async def test_execute_delete_vm(mock_delete_vm):
    """Test executing delete_vm tool."""
    # Mock the VM deletion response
    mock_response = json.dumps({
        "status": "success",
        "message": "Docker container 'test-vm' deleted successfully"
    })
    mock_delete_vm.return_value = mock_response
    
    result = await execute_tool("delete_vm", {
        "platform": "docker",
        "vm_name": "test-vm",
        "target_host": "192.168.1.50",
        "ssh_user": "admin",
        "ssh_password": "password123"
    })
    
    assert "content" in result
    assert len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"
    
    # Parse the JSON response
    response_data = json.loads(result["content"][0]["text"])
    assert response_data["status"] == "success"
    assert "deleted successfully" in response_data["message"]
    
    # Verify the function was called with correct arguments
    mock_delete_vm.assert_called_once_with(
        platform="docker",
        vm_name="test-vm",
        target_host="192.168.1.50",
        ssh_user="admin",
        ssh_password="password123"
    )


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_manager.list_vms_on_host')
async def test_execute_list_vms(mock_list_vms):
    """Test executing list_vms tool."""
    # Mock the VM listing response
    mock_response = json.dumps({
        "status": "success",
        "host": "192.168.1.50",
        "total_vms": 3,
        "vms": [
            {
                "platform": "docker",
                "name": "web-server",
                "status": "Up 2 hours",
                "ports": "0.0.0.0:8080->80/tcp"
            },
            {
                "platform": "lxd",
                "name": "database-server",
                "status": "Running",
                "ip": "192.168.1.101"
            },
            {
                "platform": "docker",
                "name": "api-server",
                "status": "Up 1 day",
                "ports": "0.0.0.0:3000->3000/tcp"
            }
        ]
    })
    mock_list_vms.return_value = mock_response
    
    result = await execute_tool("list_vms", {
        "target_host": "192.168.1.50",
        "ssh_user": "admin",
        "ssh_password": "password123",
        "platforms": ["docker", "lxd"]
    })
    
    assert "content" in result
    assert len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"
    
    # Parse the JSON response
    response_data = json.loads(result["content"][0]["text"])
    assert response_data["status"] == "success"
    assert response_data["host"] == "192.168.1.50"
    assert response_data["total_vms"] == 3
    assert len(response_data["vms"]) == 3
    
    # Check VM details
    vms = response_data["vms"]
    docker_vms = [vm for vm in vms if vm["platform"] == "docker"]
    lxd_vms = [vm for vm in vms if vm["platform"] == "lxd"]
    assert len(docker_vms) == 2
    assert len(lxd_vms) == 1
    
    # Verify the function was called with correct arguments
    mock_list_vms.assert_called_once_with(
        target_host="192.168.1.50",
        ssh_user="admin",
        ssh_password="password123",
        platforms=["docker", "lxd"]
    )


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_manager.deploy_vm_on_platform')
async def test_deploy_vm_with_error(mock_deploy_vm):
    """Test deploy_vm tool handles errors gracefully."""
    # Mock an error response
    mock_response = json.dumps({
        "status": "error",
        "message": "Docker daemon not running on target host"
    })
    mock_deploy_vm.return_value = mock_response
    
    result = await execute_tool("deploy_vm", {
        "platform": "docker",
        "vm_name": "failing-vm",
        "target_host": "192.168.1.50",
        "ssh_user": "admin",
        "ssh_password": "password123"
    })
    
    assert "content" in result
    response_data = json.loads(result["content"][0]["text"])
    assert response_data["status"] == "error"
    assert "Docker daemon not running" in response_data["message"]


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_manager.list_vms_on_host')
async def test_list_vms_default_platforms(mock_list_vms):
    """Test list_vms tool uses default platforms when not specified."""
    mock_response = json.dumps({
        "status": "success",
        "host": "192.168.1.50", 
        "total_vms": 0,
        "vms": []
    })
    mock_list_vms.return_value = mock_response
    
    result = await execute_tool("list_vms", {
        "target_host": "192.168.1.50",
        "ssh_user": "admin",
        "ssh_password": "password123"
    })
    
    assert "content" in result
    response_data = json.loads(result["content"][0]["text"])
    assert response_data["status"] == "success"
    
    # Verify default platforms were used
    mock_list_vms.assert_called_once_with(
        target_host="192.168.1.50",
        ssh_user="admin", 
        ssh_password="password123",
        platforms=["docker", "lxd"]  # Default platforms
    )


def test_vm_operational_tool_schemas():
    """Test that VM operational tools have proper schemas."""
    tools = get_available_tools()
    
    # Test control_vm schema
    control_tool = tools["control_vm"]
    assert "description" in control_tool
    assert "Control VM/container state" in control_tool["description"]
    assert "action" in control_tool["inputSchema"]["properties"]
    action_enum = control_tool["inputSchema"]["properties"]["action"]["enum"]
    assert "start" in action_enum
    assert "stop" in action_enum
    assert "restart" in action_enum
    assert control_tool["inputSchema"]["required"] == ["platform", "vm_name", "action", "target_host", "ssh_user", "ssh_password"]
    
    # Test get_vm_status schema
    status_tool = tools["get_vm_status"]
    assert "description" in status_tool
    assert "detailed status and resource usage" in status_tool["description"]
    assert status_tool["inputSchema"]["required"] == ["platform", "vm_name", "target_host", "ssh_user", "ssh_password"]
    
    # Test get_vm_logs schema
    logs_tool = tools["get_vm_logs"]
    assert "description" in logs_tool
    assert "Get logs from a VM" in logs_tool["description"]
    assert "lines" in logs_tool["inputSchema"]["properties"]
    assert "follow" in logs_tool["inputSchema"]["properties"]
    assert logs_tool["inputSchema"]["properties"]["lines"]["default"] == 50
    assert logs_tool["inputSchema"]["properties"]["follow"]["default"] == False
    
    # Test manage_vm_services schema
    services_tool = tools["manage_vm_services"]
    assert "description" in services_tool
    assert "Manage services inside a VM" in services_tool["description"]
    assert "action" in services_tool["inputSchema"]["properties"]
    service_actions = services_tool["inputSchema"]["properties"]["action"]["enum"]
    assert "list" in service_actions
    assert "start" in service_actions
    assert "stop" in service_actions
    assert "restart" in service_actions
    assert "status" in service_actions


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_operations.control_vm_state')
async def test_execute_control_vm(mock_control_vm):
    """Test executing control_vm tool."""
    # Mock the VM control response
    mock_response = json.dumps({
        "status": "success",
        "platform": "docker",
        "vm_name": "test-vm",
        "action": "start",
        "message": "Docker container 'test-vm' start successful"
    })
    mock_control_vm.return_value = mock_response
    
    result = await execute_tool("control_vm", {
        "platform": "docker",
        "vm_name": "test-vm",
        "action": "start",
        "target_host": "192.168.1.50",
        "ssh_user": "admin",
        "ssh_password": "password123"
    })
    
    assert "content" in result
    response_data = json.loads(result["content"][0]["text"])
    assert response_data["status"] == "success"
    assert response_data["action"] == "start"
    assert response_data["vm_name"] == "test-vm"
    
    mock_control_vm.assert_called_once_with(
        platform="docker",
        vm_name="test-vm",
        action="start",
        target_host="192.168.1.50",
        ssh_user="admin",
        ssh_password="password123"
    )


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_operations.get_vm_detailed_status')
async def test_execute_get_vm_status(mock_get_status):
    """Test executing get_vm_status tool."""
    # Mock the VM status response
    mock_response = json.dumps({
        "status": "success",
        "platform": "docker",
        "vm_name": "test-vm",
        "state": {
            "running": True,
            "status": "running",
            "started_at": "2024-01-01T12:00:00Z"
        },
        "resource_usage": {
            "cpu_percent": "2.5%",
            "memory_usage": "256MB / 1GB"
        }
    })
    mock_get_status.return_value = mock_response
    
    result = await execute_tool("get_vm_status", {
        "platform": "docker",
        "vm_name": "test-vm",
        "target_host": "192.168.1.50",
        "ssh_user": "admin",
        "ssh_password": "password123"
    })
    
    assert "content" in result
    response_data = json.loads(result["content"][0]["text"])
    assert response_data["status"] == "success"
    assert response_data["state"]["running"] == True
    assert response_data["resource_usage"]["cpu_percent"] == "2.5%"


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_operations.get_vm_logs')
async def test_execute_get_vm_logs(mock_get_logs):
    """Test executing get_vm_logs tool."""
    # Mock the VM logs response
    mock_response = json.dumps({
        "status": "success",
        "platform": "docker",
        "vm_name": "test-vm",
        "logs": "2024-01-01 12:00:00 Starting application\n2024-01-01 12:00:01 Application ready",
        "lines_requested": 50,
        "follow_mode": False
    })
    mock_get_logs.return_value = mock_response
    
    result = await execute_tool("get_vm_logs", {
        "platform": "docker",
        "vm_name": "test-vm",
        "target_host": "192.168.1.50",
        "ssh_user": "admin",
        "ssh_password": "password123",
        "lines": 50,
        "follow": False
    })
    
    assert "content" in result
    response_data = json.loads(result["content"][0]["text"])
    assert response_data["status"] == "success"
    assert response_data["lines_requested"] == 50
    assert response_data["follow_mode"] == False
    assert "Starting application" in response_data["logs"]
    
    mock_get_logs.assert_called_once_with(
        platform="docker",
        vm_name="test-vm",
        target_host="192.168.1.50",
        ssh_user="admin",
        ssh_password="password123",
        lines=50,
        follow=False
    )


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_operations.manage_vm_services')
async def test_execute_manage_vm_services(mock_manage_services):
    """Test executing manage_vm_services tool."""
    # Mock the service management response
    mock_response = json.dumps({
        "status": "success",
        "platform": "docker",
        "vm_name": "test-vm",
        "action": "list",
        "services": [
            {"name": "ssh", "active": "active", "sub": "running"},
            {"name": "nginx", "active": "active", "sub": "running"}
        ],
        "total_services": 2
    })
    mock_manage_services.return_value = mock_response
    
    result = await execute_tool("manage_vm_services", {
        "platform": "docker",
        "vm_name": "test-vm",
        "action": "list",
        "target_host": "192.168.1.50",
        "ssh_user": "admin",
        "ssh_password": "password123"
    })
    
    assert "content" in result
    response_data = json.loads(result["content"][0]["text"])
    assert response_data["status"] == "success"
    assert response_data["action"] == "list"
    assert response_data["total_services"] == 2
    assert len(response_data["services"]) == 2
    
    mock_manage_services.assert_called_once_with(
        platform="docker",
        vm_name="test-vm",
        action="list",
        target_host="192.168.1.50",
        ssh_user="admin",
        ssh_password="password123",
        service_name=None
    )


@pytest.mark.asyncio
@patch('src.homelab_mcp.vm_operations.manage_vm_services')
async def test_execute_manage_vm_services_with_service_name(mock_manage_services):
    """Test managing specific service."""
    mock_response = json.dumps({
        "status": "success",
        "platform": "lxd",
        "vm_name": "test-vm",
        "action": "restart",
        "service_name": "nginx",
        "message": "Service 'nginx' restart successful"
    })
    mock_manage_services.return_value = mock_response
    
    result = await execute_tool("manage_vm_services", {
        "platform": "lxd",
        "vm_name": "test-vm",
        "action": "restart",
        "service_name": "nginx",
        "target_host": "192.168.1.50",
        "ssh_user": "admin",
        "ssh_password": "password123"
    })
    
    assert "content" in result
    response_data = json.loads(result["content"][0]["text"])
    assert response_data["status"] == "success"
    assert response_data["action"] == "restart"
    assert response_data["service_name"] == "nginx"
    
    mock_manage_services.assert_called_once_with(
        platform="lxd",
        vm_name="test-vm",
        action="restart",
        target_host="192.168.1.50",
        ssh_user="admin",
        ssh_password="password123",
        service_name="nginx"
    )
