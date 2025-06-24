"""Tests for SSH tools."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncssh
from src.homelab_mcp.ssh_tools import (
    ssh_discover_system,
    ensure_mcp_ssh_key,
    setup_remote_mcp_admin,
    verify_mcp_admin_access,
    get_mcp_ssh_key_path,
    get_mcp_public_key_path
)


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


@pytest.mark.asyncio
@patch('src.homelab_mcp.ssh_tools.Path.exists')
@patch('src.homelab_mcp.ssh_tools.Path.mkdir')
@patch('src.homelab_mcp.ssh_tools.Path.chmod')
@patch('builtins.open', create=True)
@patch('src.homelab_mcp.ssh_tools.asyncssh.generate_private_key')
async def test_ensure_mcp_ssh_key_creates_new(mock_generate, mock_open, mock_chmod, mock_mkdir, mock_exists):
    """Test SSH key generation when keys don't exist."""
    # Mock that keys don't exist
    mock_exists.return_value = False
    
    # Mock key generation
    mock_private_key = MagicMock()
    mock_private_key.export_private_key.return_value = b'private_key_data'
    mock_private_key.export_public_key.return_value = b'public_key_data'
    mock_generate.return_value = mock_private_key
    
    # Mock file operations
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file
    
    # Execute
    result = await ensure_mcp_ssh_key()
    
    # Verify key generation
    mock_generate.assert_called_once_with('ssh-rsa', key_size=2048)
    
    # Verify directory creation
    mock_mkdir.assert_called_once_with(mode=0o700, exist_ok=True)
    
    # Verify file writes
    assert mock_open.call_count == 2
    assert mock_chmod.call_count == 2
    
    # Verify result
    assert str(get_mcp_ssh_key_path()) in result


@pytest.mark.asyncio
@patch('src.homelab_mcp.ssh_tools.Path.exists')
async def test_ensure_mcp_ssh_key_uses_existing(mock_exists):
    """Test that existing SSH keys are reused."""
    # Mock that keys exist
    mock_exists.return_value = True
    
    # Execute
    result = await ensure_mcp_ssh_key()
    
    # Verify result points to existing key
    assert str(get_mcp_ssh_key_path()) in result


@pytest.mark.asyncio
@patch('src.homelab_mcp.ssh_tools.ensure_mcp_ssh_key')
@patch('src.homelab_mcp.ssh_tools.get_mcp_public_key_path')
@patch('builtins.open', create=True)
@patch('src.homelab_mcp.ssh_tools.asyncssh.connect')
async def test_setup_remote_mcp_admin_success(mock_connect, mock_open, mock_pub_key_path, mock_ensure_key):
    """Test successful remote mcp_admin setup."""
    # Mock SSH key
    mock_ensure_key.return_value = "/home/user/.ssh/mcp_admin_rsa"
    mock_pub_key_path.return_value.exists.return_value = True
    
    # Mock public key read
    mock_file = MagicMock()
    mock_file.read.return_value = "ssh-rsa AAAAB3... mcp_admin@host"
    mock_open.return_value.__enter__.return_value = mock_file
    
    # Mock SSH connection and commands
    mock_conn = AsyncMock()
    
    # Mock command results - need to match the actual sequence in the function
    user_check = MagicMock()
    user_check.exit_status = 1  # User doesn't exist
    
    cleanup_home = MagicMock()  # sudo rm -rf /home/mcp_admin
    cleanup_home.exit_status = 0
    
    create_user = MagicMock()
    create_user.exit_status = 0
    
    chown_home = MagicMock()  # sudo chown -R mcp_admin:mcp_admin /home/mcp_admin
    chown_home.exit_status = 0
    
    sudo_group = MagicMock()
    sudo_group.exit_status = 0
    
    key_check = MagicMock()
    key_check.exit_status = 1  # Key doesn't exist
    
    mkdir_home = MagicMock()  # sudo mkdir -p /home/mcp_admin
    mkdir_home.exit_status = 0
    
    chown_home2 = MagicMock()  # sudo chown mcp_admin:mcp_admin /home/mcp_admin
    chown_home2.exit_status = 0
    
    mkdir_cmd = MagicMock()  # create .ssh directory
    mkdir_cmd.exit_status = 0
    
    add_key = MagicMock()
    add_key.exit_status = 0
    
    sudoers_setup = MagicMock()
    sudoers_setup.exit_status = 0
    
    test_conn = MagicMock()
    test_conn.exit_status = 0
    
    mock_conn.run.side_effect = [user_check, cleanup_home, create_user, chown_home, sudo_group, key_check, mkdir_home, chown_home2, mkdir_cmd, add_key, sudoers_setup, test_conn]
    
    # Setup context manager
    async def mock_context_mgr():
        class MockContext:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        return MockContext()
    
    # Make connect return the async context manager
    mock_connect.side_effect = lambda **kwargs: mock_context_mgr()
    
    # Execute
    result = await setup_remote_mcp_admin("test-host", "admin", "password")
    
    # Parse result
    result_data = json.loads(result)
    
    # Verify success
    assert result_data["status"] == "success"
    assert result_data["hostname"] == "test-host"
    assert "mcp_admin_setup" in result_data
    assert result_data["mcp_admin_setup"]["user_creation"] == "Success: mcp_admin user created"
    assert result_data["mcp_admin_setup"]["sudo_access"] == "Success: Added to sudo group"
    assert result_data["mcp_admin_setup"]["ssh_key"] == "Success: SSH key installed"
    assert result_data["mcp_admin_setup"]["passwordless_sudo"] == "Success: Passwordless sudo enabled"
    assert result_data["mcp_admin_setup"]["test_access"] == "Success: mcp_admin access verified"


@pytest.mark.asyncio
@patch('src.homelab_mcp.ssh_tools.ensure_mcp_ssh_key')
@patch('src.homelab_mcp.ssh_tools.get_mcp_public_key_path')
@patch('builtins.open', create=True)
@patch('src.homelab_mcp.ssh_tools.asyncssh.connect')
async def test_setup_remote_mcp_admin_user_exists(mock_connect, mock_open, mock_pub_key_path, mock_ensure_key):
    """Test remote mcp_admin setup when user already exists."""
    # Mock SSH key
    mock_ensure_key.return_value = "/home/user/.ssh/mcp_admin_rsa"
    mock_pub_key_path.return_value.exists.return_value = True
    
    # Mock public key read
    mock_file = MagicMock()
    mock_file.read.return_value = "ssh-rsa AAAAB3... mcp_admin@host"
    mock_open.return_value.__enter__.return_value = mock_file
    
    # Mock SSH connection and commands
    mock_conn = AsyncMock()
    
    # Mock command results - for when user already exists
    user_check = MagicMock()
    user_check.exit_status = 0  # User exists
    
    sudo_group = MagicMock()
    sudo_group.exit_status = 0
    
    key_check = MagicMock()
    key_check.exit_status = 1  # Key doesn't exist
    
    mkdir_home = MagicMock()  # sudo mkdir -p /home/mcp_admin
    mkdir_home.exit_status = 0
    
    chown_home = MagicMock()  # sudo chown mcp_admin:mcp_admin /home/mcp_admin
    chown_home.exit_status = 0
    
    mkdir_cmd = MagicMock()  # create .ssh directory
    mkdir_cmd.exit_status = 0
    
    add_key = MagicMock()
    add_key.exit_status = 0
    
    sudoers_setup = MagicMock()
    sudoers_setup.exit_status = 0
    
    test_conn = MagicMock()
    test_conn.exit_status = 0
    
    mock_conn.run.side_effect = [user_check, sudo_group, key_check, mkdir_home, chown_home, mkdir_cmd, add_key, sudoers_setup, test_conn]
    
    # Setup context manager
    async def mock_context_mgr():
        class MockContext:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        return MockContext()
    
    # Make connect return the async context manager
    mock_connect.side_effect = lambda **kwargs: mock_context_mgr()
    
    # Execute
    result = await setup_remote_mcp_admin("test-host", "admin", "password")
    
    # Parse result
    result_data = json.loads(result)
    
    # Verify success
    assert result_data["status"] == "success"
    assert result_data["mcp_admin_setup"]["user_creation"] == "User already exists"


@pytest.mark.asyncio
@patch('src.homelab_mcp.ssh_tools.get_mcp_ssh_key_path')
@patch('src.homelab_mcp.ssh_tools.asyncssh.connect')
async def test_verify_mcp_admin_access_success(mock_connect, mock_key_path):
    """Test successful mcp_admin access verification."""
    # Mock SSH key exists
    mock_key_path.return_value.exists.return_value = True
    
    # Mock SSH connection and commands
    mock_conn = AsyncMock()
    
    # Mock command results
    whoami_result = MagicMock()
    whoami_result.exit_status = 0
    whoami_result.stdout = "mcp_admin"
    
    sudo_result = MagicMock()
    sudo_result.exit_status = 0
    
    hostname_result = MagicMock()
    hostname_result.exit_status = 0
    hostname_result.stdout = "test-server"
    
    mock_conn.run.side_effect = [whoami_result, sudo_result, hostname_result]
    
    # Setup context manager
    async def mock_context_mgr():
        class MockContext:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        return MockContext()
    
    # Make connect return the async context manager
    mock_connect.side_effect = lambda **kwargs: mock_context_mgr()
    
    # Execute
    result = await verify_mcp_admin_access("test-host")
    
    # Parse result
    result_data = json.loads(result)
    
    # Verify success
    assert result_data["status"] == "success"
    assert result_data["hostname"] == "test-server"
    assert result_data["connection_ip"] == "test-host"
    assert result_data["mcp_admin"]["ssh_access"] == "Success: Connected with SSH key"
    assert result_data["mcp_admin"]["sudo_access"] == "Success: Passwordless sudo working"
    assert result_data["mcp_admin"]["username"] == "mcp_admin"


@pytest.mark.asyncio
@patch('src.homelab_mcp.ssh_tools.get_mcp_ssh_key_path')
async def test_verify_mcp_admin_access_no_key(mock_key_path):
    """Test verification when SSH key doesn't exist."""
    # Mock SSH key doesn't exist
    mock_key_path.return_value.exists.return_value = False
    
    # Execute
    result = await verify_mcp_admin_access("test-host")
    
    # Parse result
    result_data = json.loads(result)
    
    # Verify error
    assert result_data["status"] == "error"
    assert "SSH key not found" in result_data["error"]


@pytest.mark.asyncio
@patch('src.homelab_mcp.ssh_tools.get_mcp_ssh_key_path')
@patch('src.homelab_mcp.ssh_tools.asyncssh.connect')
async def test_verify_mcp_admin_access_auth_failure(mock_connect, mock_key_path):
    """Test verification with authentication failure."""
    # Mock SSH key exists
    mock_key_path.return_value.exists.return_value = True
    
    # Mock connection failure
    mock_connect.side_effect = asyncssh.misc.PermissionDenied("Authentication failed")
    
    # Execute
    result = await verify_mcp_admin_access("test-host")
    
    # Parse result
    result_data = json.loads(result)
    
    # Verify error
    assert result_data["status"] == "error"
    assert "SSH key authentication failed" in result_data["error"]


@pytest.mark.asyncio
@patch('src.homelab_mcp.ssh_tools.get_mcp_ssh_key_path')
@patch('src.homelab_mcp.ssh_tools.asyncssh.connect')
async def test_ssh_discover_with_mcp_admin_auto_key(mock_connect, mock_key_path):
    """Test SSH discovery auto-uses MCP key for mcp_admin user."""
    # Mock SSH key exists
    mock_key_path.return_value.exists.return_value = True
    mock_key_path.return_value.__str__.return_value = "/home/user/.ssh/mcp_admin_rsa"
    
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
    
    # Execute discovery as mcp_admin without password
    result = await ssh_discover_system(
        hostname="test-host",
        username="mcp_admin"
    )
    
    # Verify result is valid JSON
    result_data = json.loads(result)
    assert "status" in result_data
    
    # Verify connect was called with MCP key
    mock_connect.assert_called_once()
    call_args = mock_connect.call_args[1]
    assert call_args["client_keys"] == ["/home/user/.ssh/mcp_admin_rsa"]
    assert "password" not in call_args


@pytest.mark.asyncio
@patch('src.homelab_mcp.ssh_tools.ensure_mcp_ssh_key')
@patch('src.homelab_mcp.ssh_tools.get_mcp_public_key_path')
@patch('builtins.open', create=True)
@patch('src.homelab_mcp.ssh_tools.asyncssh.connect')
async def test_setup_remote_mcp_admin_force_update_key(mock_connect, mock_open, mock_pub_key_path, mock_ensure_key):
    """Test remote mcp_admin setup with force key update."""
    # Mock SSH key
    mock_ensure_key.return_value = "/home/user/.ssh/mcp_admin_rsa"
    mock_pub_key_path.return_value.exists.return_value = True
    
    # Mock public key read
    mock_file = MagicMock()
    mock_file.read.return_value = "ssh-rsa AAAAB3NEW... mcp_admin@host"
    mock_open.return_value.__enter__.return_value = mock_file
    
    # Mock SSH connection and commands
    mock_conn = AsyncMock()
    
    # Mock command results - for existing user with force update key
    user_check = MagicMock()
    user_check.exit_status = 0  # User exists
    
    sudo_group = MagicMock()
    sudo_group.exit_status = 0
    
    key_check = MagicMock()
    key_check.exit_status = 0  # Key exists (but different)
    
    mkdir_home = MagicMock()  # sudo mkdir -p /home/mcp_admin
    mkdir_home.exit_status = 0
    
    chown_home = MagicMock()  # sudo chown mcp_admin:mcp_admin /home/mcp_admin
    chown_home.exit_status = 0
    
    mkdir_cmd = MagicMock()  # create .ssh directory
    mkdir_cmd.exit_status = 0
    
    remove_old = MagicMock()  # Remove old key
    remove_old.exit_status = 0
    
    add_key = MagicMock()
    add_key.exit_status = 0
    
    sudoers_setup = MagicMock()
    sudoers_setup.exit_status = 0
    
    test_conn = MagicMock()
    test_conn.exit_status = 0
    
    mock_conn.run.side_effect = [user_check, sudo_group, key_check, mkdir_home, chown_home, mkdir_cmd, remove_old, add_key, sudoers_setup, test_conn]
    
    # Setup context manager
    async def mock_context_mgr():
        class MockContext:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        return MockContext()
    
    # Make connect return the async context manager
    mock_connect.side_effect = lambda **kwargs: mock_context_mgr()
    
    # Execute with force_update_key=True (default)
    result = await setup_remote_mcp_admin("test-host", "admin", "password")
    
    # Parse result
    result_data = json.loads(result)
    
    # Verify success
    assert result_data["status"] == "success"
    assert result_data["mcp_admin_setup"]["user_creation"] == "User already exists"
    assert result_data["mcp_admin_setup"]["ssh_key"] == "Success: SSH key updated"


@pytest.mark.asyncio
@patch('src.homelab_mcp.ssh_tools.ensure_mcp_ssh_key')
@patch('src.homelab_mcp.ssh_tools.get_mcp_public_key_path')
@patch('builtins.open', create=True)
@patch('src.homelab_mcp.ssh_tools.asyncssh.connect')
async def test_setup_remote_mcp_admin_no_force_update(mock_connect, mock_open, mock_pub_key_path, mock_ensure_key):
    """Test remote mcp_admin setup without forcing key update."""
    # Mock SSH key
    mock_ensure_key.return_value = "/home/user/.ssh/mcp_admin_rsa"
    mock_pub_key_path.return_value.exists.return_value = True
    
    # Mock public key read
    mock_file = MagicMock()
    mock_file.read.return_value = "ssh-rsa AAAAB3... mcp_admin@host"
    mock_open.return_value.__enter__.return_value = mock_file
    
    # Mock SSH connection and commands
    mock_conn = AsyncMock()
    
    # Mock command results
    user_check = MagicMock()
    user_check.exit_status = 0  # User exists
    
    sudo_group = MagicMock()
    sudo_group.exit_status = 0
    
    key_check = MagicMock()
    key_check.exit_status = 0  # Key already exists
    
    sudoers_setup = MagicMock()
    sudoers_setup.exit_status = 0
    
    test_conn = MagicMock()
    test_conn.exit_status = 0
    
    mock_conn.run.side_effect = [user_check, sudo_group, key_check, sudoers_setup, test_conn]
    
    # Setup context manager
    async def mock_context_mgr():
        class MockContext:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        return MockContext()
    
    # Make connect return the async context manager
    mock_connect.side_effect = lambda **kwargs: mock_context_mgr()
    
    # Execute with force_update_key=False
    result = await setup_remote_mcp_admin("test-host", "admin", "password", force_update_key=False)
    
    # Parse result
    result_data = json.loads(result)
    
    # Verify success
    assert result_data["status"] == "success"
    assert result_data["mcp_admin_setup"]["ssh_key"] == "SSH key already exists"