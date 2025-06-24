"""Tests for MCP tools."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.homelab_mcp.tools import get_available_tools, execute_tool


def test_get_available_tools():
    """Test getting available tools."""
    tools = get_available_tools()
    
    assert len(tools) == 10  # Original 4 + 6 new sitemap tools
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