"""Tests for the MCP server."""

import json
import pytest
from unittest.mock import AsyncMock, patch
from src.homelab_mcp.server import HomelabMCPServer


@pytest.mark.asyncio
@patch('src.homelab_mcp.server.ensure_mcp_ssh_key')
async def test_server_initialize(mock_ensure_key):
    """Test server initialization response."""
    server = HomelabMCPServer()
    
    # Mock SSH key generation
    mock_ensure_key.return_value = "/home/user/.ssh/mcp_admin_rsa"
    
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }
    
    response = await server.handle_request(request)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    assert response["result"]["protocolVersion"] == "2024-11-05"
    assert response["result"]["serverInfo"]["name"] == "homelab-mcp"
    
    # Verify SSH key was generated on first initialization
    mock_ensure_key.assert_called_once()
    
    # Second initialization should not regenerate key
    response2 = await server.handle_request(request)
    assert response2["jsonrpc"] == "2.0"
    mock_ensure_key.assert_called_once()  # Still only called once


@pytest.mark.asyncio
async def test_tools_list():
    """Test listing available tools."""
    server = HomelabMCPServer()
    
    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    response = await server.handle_request(request)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 2
    assert "result" in response
    assert "tools" in response["result"]
    
    tools = response["result"]["tools"]
    assert len(tools) == 34  # All tools including SSH, sitemap, infrastructure, VM, service, and Ansible tools
    
    # Check tool names and descriptions
    tool_names = [tool.get("description") for tool in tools]
    assert any("SSH" in desc for desc in tool_names)
    assert any("setup mcp_admin" in desc for desc in tool_names)
    assert any("Verify" in desc for desc in tool_names)
    
    # Check new sitemap tools are included
    assert any("network site map" in desc for desc in tool_names)
    assert any("topology" in desc for desc in tool_names)
    assert any("deployment" in desc for desc in tool_names)


@pytest.mark.asyncio
async def test_unknown_method():
    """Test handling of unknown method."""
    server = HomelabMCPServer()
    
    request = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "unknown/method",
        "params": {}
    }
    
    response = await server.handle_request(request)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 4
    assert "error" in response
    assert response["error"]["code"] == -32603
    assert "Unknown method" in response["error"]["message"]


@pytest.mark.asyncio
async def test_unknown_tool():
    """Test handling of unknown tool."""
    server = HomelabMCPServer()
    
    request = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "nonexistent_tool"
        }
    }
    
    response = await server.handle_request(request)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 5
    assert "error" in response
    assert "Unknown tool" in response["error"]["message"]


@pytest.mark.asyncio
async def test_ssh_discover_tool_missing_params():
    """Test ssh_discover tool with missing required parameters."""
    server = HomelabMCPServer()
    
    request = {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "name": "ssh_discover",
            "arguments": {
                "hostname": "192.168.1.100"
                # Missing username
            }
        }
    }
    
    response = await server.handle_request(request)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 6
    assert "error" in response or "error" in json.loads(response["result"]["content"][0]["text"])