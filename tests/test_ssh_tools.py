"""Tests for SSH tools."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncssh
from src.homelab_mcp.ssh_tools import ssh_discover_system


@pytest.mark.asyncio
@patch('src.homelab_mcp.ssh_tools.asyncssh.connect')
async def test_ssh_discover_success(mock_connect):
    """Test successful SSH discovery."""
    # Mock command results
    hostname_result = MagicMock()
    hostname_result.exit_status = 0
    hostname_result.stdout = "raspberrypi"
    
    cpu_result = MagicMock()
    cpu_result.exit_status = 0
    cpu_result.stdout = "model name\t: Intel Core i5\n4"
    
    mem_result = MagicMock()
    mem_result.exit_status = 0
    mem_result.stdout = """              total        used        free      shared  buff/cache   available
Mem:           7.7G        2.1G        3.9G        123M        1.7G        5.3G"""
    
    disk_result = MagicMock()
    disk_result.exit_status = 0
    disk_result.stdout = """Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        20G  5.5G   14G  30% /"""
    
    net_result = MagicMock()
    net_result.exit_status = 0
    net_result.stdout = json.dumps([
        {
            "ifname": "eth0",
            "operstate": "UP",
            "addr_info": [
                {"family": "inet", "local": "192.168.1.100"}
            ]
        }
    ])
    
    uptime_result = MagicMock()
    uptime_result.exit_status = 0
    uptime_result.stdout = "up 2 days, 3 hours, 45 minutes"
    
    os_result = MagicMock()
    os_result.exit_status = 0
    os_result.stdout = 'PRETTY_NAME="Ubuntu 22.04.3 LTS"'
    
    # Create mock connection
    mock_conn = AsyncMock()
    call_count = 0
    
    async def mock_run(*args, **kwargs):
        nonlocal call_count
        results = [hostname_result, cpu_result, mem_result, disk_result, net_result, uptime_result, os_result]
        result = results[call_count]
        call_count += 1
        return result
    
    mock_conn.run = mock_run
    
    # Create an async context manager that returns mock_conn
    async def mock_context_mgr():
        class MockContext:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        return MockContext()
    
    # Make connect return the async context manager
    mock_connect.side_effect = lambda **kwargs: mock_context_mgr()
    
    # Execute discovery
    result = await ssh_discover_system(
        hostname="test-host",
        username="test-user",
        password="test-pass"
    )
    
    # Parse result
    result_data = json.loads(result)
    
    # Verify structure
    assert result_data["status"] == "success"
    assert result_data["hostname"] == "raspberrypi"  # Actual hostname from remote system
    assert result_data["connection_ip"] == "test-host"  # IP used to connect
    assert "data" in result_data
    
    # Verify CPU info
    assert "cpu" in result_data["data"]
    assert result_data["data"]["cpu"]["model"] == "Intel Core i5"
    assert result_data["data"]["cpu"]["cores"] == "4"
    
    # Verify memory info
    assert "memory" in result_data["data"]
    assert result_data["data"]["memory"]["total"] == "7.7G"
    assert result_data["data"]["memory"]["used"] == "2.1G"
    
    # Verify disk info
    assert "disk" in result_data["data"]
    assert result_data["data"]["disk"]["size"] == "20G"
    assert result_data["data"]["disk"]["use_percent"] == "30%"
    
    # Verify network info
    assert "network" in result_data["data"]
    assert len(result_data["data"]["network"]) == 1
    assert result_data["data"]["network"][0]["name"] == "eth0"
    assert "192.168.1.100" in result_data["data"]["network"][0]["addresses"]
    
    # Verify uptime and OS
    assert result_data["data"]["uptime"] == "up 2 days, 3 hours, 45 minutes"
    assert result_data["data"]["os"] == "Ubuntu 22.04.3 LTS"


@pytest.mark.asyncio
@patch('asyncssh.connect')
async def test_ssh_discover_auth_failure(mock_connect):
    """Test SSH discovery with authentication failure."""
    mock_connect.side_effect = asyncssh.misc.PermissionDenied("Authentication failed")
    
    result = await ssh_discover_system(
        hostname="test-host",
        username="test-user",
        password="wrong-pass"
    )
    
    result_data = json.loads(result)
    assert result_data["status"] == "error"
    assert result_data["connection_ip"] == "test-host"
    assert "authentication failed" in result_data["error"].lower()


@pytest.mark.asyncio
@patch('asyncssh.connect')
async def test_ssh_discover_connection_timeout(mock_connect):
    """Test SSH discovery with connection timeout."""
    import asyncio
    mock_connect.side_effect = asyncio.TimeoutError()
    
    result = await ssh_discover_system(
        hostname="unreachable-host",
        username="test-user",
        password="test-pass"
    )
    
    result_data = json.loads(result)
    assert result_data["status"] == "error"
    assert result_data["connection_ip"] == "unreachable-host"
    assert "timeout" in result_data["error"].lower()


@pytest.mark.asyncio
async def test_ssh_discover_no_credentials():
    """Test SSH discovery without password or key."""
    result = await ssh_discover_system(
        hostname="test-host",
        username="test-user"
    )
    
    result_data = json.loads(result)
    assert result_data["status"] == "error"
    assert "password or key_path must be provided" in result_data["error"]


@pytest.mark.asyncio
@patch('asyncssh.connect')
async def test_ssh_discover_with_key_path(mock_connect):
    """Test SSH discovery using key file."""
    # Mock SSH connection
    mock_conn = AsyncMock()
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_conn
    mock_context.__aexit__.return_value = None
    mock_connect.return_value = mock_context
    
    # Mock minimal command results
    mock_result = MagicMock()
    mock_result.exit_status = 1  # Commands fail
    mock_result.stdout = None
    mock_conn.run.return_value = mock_result
    
    # Execute discovery with key
    result = await ssh_discover_system(
        hostname="test-host",
        username="test-user",
        key_path="/path/to/key"
    )
    
    # Verify connect was called with key
    mock_connect.assert_called_once()
    call_args = mock_connect.call_args[1]
    assert call_args["client_keys"] == ["/path/to/key"]
    assert "password" not in call_args