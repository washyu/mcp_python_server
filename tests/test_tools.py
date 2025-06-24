"""Tests for MCP tools."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.homelab_mcp.tools import get_available_tools, execute_tool


def test_get_available_tools():
    """Test getting available tools."""
    tools = get_available_tools()
    
    assert len(tools) == 2
    assert "hello_world" in tools
    assert "ssh_discover" in tools
    
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