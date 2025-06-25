# Homelab MCP Server

A Model Context Protocol (MCP) server for managing and monitoring homelab systems via SSH.

## Overview

This MCP server provides tools for AI assistants to discover and monitor systems in your homelab environment. It follows the MCP specification for stdio-based communication.

## Features

- **System Discovery**: SSH into systems to gather hardware and software information
- **SSH Key Management**: Automatic SSH key generation for secure authentication
- **Remote Setup**: Automatically configure remote systems with mcp_admin user
- **Standardized Interface**: Follows the MCP protocol for tool interaction
- **Extensible**: Easy to add new tools and capabilities

## Available Tools (23 Total)

### SSH & Admin Tools (4)

#### `hello_world`
A simple test tool that returns a greeting message.

#### `ssh_discover`
SSH into a remote system and gather comprehensive system information including:
- CPU details (model, cores)
- Memory usage
- Disk usage
- Network interfaces
- Operating system information
- System uptime

**Note**: When using username `mcp_admin`, the tool automatically uses the MCP's SSH key if available. No password is required after running `setup_mcp_admin` on the target system.

#### `setup_mcp_admin`
SSH into a remote system using admin credentials and set up the `mcp_admin` user with:
- User creation (if not exists)
- Sudo group membership
- SSH key authentication (using MCP's generated key)
- Passwordless sudo access

Parameters:
- `hostname`: Target system IP or hostname
- `username`: Admin username with sudo access
- `password`: Admin password
- `force_update_key` (optional, default: true): Force update SSH key even if mcp_admin already has other keys

#### `verify_mcp_admin`
Verify SSH key access to the `mcp_admin` account on a remote system:
- Tests SSH key authentication
- Verifies sudo privileges
- Returns connection status

### Network Discovery Tools (6)

#### `discover_and_map`
Discover a device via SSH and store it in the network site map database.

#### `bulk_discover_and_map`
Discover multiple devices via SSH and store them in the network site map database.

#### `get_network_sitemap`
Get all discovered devices from the network site map database.

#### `analyze_network_topology`
Analyze the network topology and provide insights about the discovered devices.

#### `suggest_deployments`
Suggest optimal deployment locations based on current network topology and device capabilities.

#### `get_device_changes`
Get change history for a specific device.

### Infrastructure CRUD Tools (7)

#### `deploy_infrastructure`
Deploy new infrastructure based on AI recommendations or user specifications:
- Deploy Docker containers, LXD containers, or systemd services
- Configure networking, storage, and environment variables
- Validate deployment plans before execution

#### `update_device_config`
Update configuration of an existing device:
- Modify service configurations
- Update network settings
- Change security configurations
- Adjust resource allocations

#### `decommission_device`
Safely remove a device from the network infrastructure:
- Analyze dependencies and critical services
- Execute migration plans to move services
- Graceful shutdown and removal

#### `scale_services`
Scale services up or down based on resource analysis:
- Horizontal scaling of containers/VMs
- Resource allocation adjustments
- Load balancing configuration

#### `validate_infrastructure_changes`
Validate infrastructure changes before applying them:
- Basic, comprehensive, and simulation validation levels
- Dependency checking
- Risk assessment

#### `create_infrastructure_backup`
Create a backup of current infrastructure state:
- Full or partial backups
- Device-specific backups
- Configuration and data backup options

#### `rollback_infrastructure_changes`
Rollback recent infrastructure changes:
- Restore from backups
- Selective rollback capabilities
- Validation before rollback

### VM Management Tools (6)

#### `deploy_vm`
Deploy a new VM/container on a specific device:
- Support for Docker containers and LXD VMs
- Configurable images, ports, volumes, environment variables
- Platform-agnostic deployment

#### `control_vm`
Control VM state (start, stop, restart):
- Manage VM lifecycle
- Support for both Docker and LXD platforms
- Real-time status updates

#### `get_vm_status`
Get detailed status of a specific VM:
- Container/VM health information
- Resource usage statistics
- Network and storage details

#### `list_vms`
List all VMs/containers on a device:
- Cross-platform inventory
- Status and configuration overview
- Multi-device support

#### `get_vm_logs`
Get logs from a specific VM/container:
- Configurable log line limits
- Support for Docker and LXD logs
- Real-time log streaming

#### `remove_vm`
Remove a VM/container from a device:
- Graceful or forced removal
- Data preservation options
- Cleanup of associated resources

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd mcp_python_server
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. For development (includes testing tools):
```bash
pip install -r requirements-dev.txt
```

## Usage

### Running the Server

```bash
python run_server.py
```

The server communicates via stdio (stdin/stdout) using the MCP protocol.

### SSH Key Management

The MCP server automatically generates an SSH key pair on first initialization:
- Private key: `~/.ssh/mcp_admin_rsa`
- Public key: `~/.ssh/mcp_admin_rsa.pub`

This key is used for:
1. Authenticating as `mcp_admin` on remote systems after setup
2. Enabling passwordless SSH access for system management
3. Automatic authentication when using `ssh_discover` with username `mcp_admin`

### Testing with JSON-RPC

You can test the server by sending JSON-RPC requests:

```bash
# List available tools
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python run_server.py

# Call hello_world tool
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"hello_world"}}' | python run_server.py

# Discover a system via SSH (with password)
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"ssh_discover","arguments":{"hostname":"192.168.1.100","username":"user","password":"pass"}}}' | python run_server.py

# Discover using mcp_admin (no password needed after setup)
echo '{"jsonrpc":"2.0","id":3b,"method":"tools/call","params":{"name":"ssh_discover","arguments":{"hostname":"192.168.1.100","username":"mcp_admin"}}}' | python run_server.py

# Setup mcp_admin on a remote system
echo '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"setup_mcp_admin","arguments":{"hostname":"192.168.1.100","username":"admin","password":"adminpass"}}}' | python run_server.py

# Verify mcp_admin access
echo '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"verify_mcp_admin","arguments":{"hostname":"192.168.1.100"}}}' | python run_server.py

# Use ssh_discover with mcp_admin (no password needed after setup)
echo '{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"ssh_discover","arguments":{"hostname":"192.168.1.100","username":"mcp_admin"}}}' | python run_server.py
```

### Integration with AI Assistants

This server is designed to work with AI assistants that support the Model Context Protocol.

**🚀 For detailed Claude setup instructions, see [CLAUDE_SETUP.md](CLAUDE_SETUP.md)**

Basic configuration for Claude Desktop:

```json
{
  "mcpServers": {
    "homelab": {
      "command": "python3",
      "args": ["/path/to/your/mcp_python_server/run_server.py"],
      "env": {
        "PYTHONPATH": "/path/to/your/mcp_python_server/src"
      }
    }
  }
}
```

Place this in:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

### Typical Workflow

1. **Initial Setup**: The MCP automatically generates its SSH key on first run
2. **Configure Remote System**: Use `setup_mcp_admin` with admin credentials to:
   - Create the `mcp_admin` user on the target system
   - Install the MCP's public key for authentication
   - Grant sudo privileges
3. **Verify Access**: Use `verify_mcp_admin` to confirm setup was successful
4. **Manage Systems**: Use `ssh_discover` with username `mcp_admin` for passwordless access

Example workflow:
```bash
# 1. Setup mcp_admin on a new system
{"method":"tools/call","params":{"name":"setup_mcp_admin","arguments":{"hostname":"192.168.1.50","username":"pi","password":"raspberry"}}}

# 2. Verify the setup worked
{"method":"tools/call","params":{"name":"verify_mcp_admin","arguments":{"hostname":"192.168.1.50"}}}

# 3. Now discover system info without needing passwords
{"method":"tools/call","params":{"name":"ssh_discover","arguments":{"hostname":"192.168.1.50","username":"mcp_admin"}}}
```

### Handling Key Updates

If the `mcp_admin` user already exists but has a different SSH key, the `setup_mcp_admin` tool will automatically update it by default. You can control this behavior:

```bash
# Force update the SSH key (default behavior)
{"method":"tools/call","params":{"name":"setup_mcp_admin","arguments":{"hostname":"192.168.1.50","username":"pi","password":"raspberry","force_update_key":true}}}

# Keep existing keys (only add if no MCP key exists)
{"method":"tools/call","params":{"name":"setup_mcp_admin","arguments":{"hostname":"192.168.1.50","username":"pi","password":"raspberry","force_update_key":false}}}
```

When `force_update_key` is true (default), the tool will:
1. Remove any existing MCP keys (identified by the `mcp_admin@` comment)
2. Add the current MCP's public key
3. Preserve any other SSH keys the user might have

## Development

### Project Structure

```
mcp_python_server/
├── src/
│   └── homelab_mcp/
│       ├── __init__.py
│       ├── server.py      # Main MCP server
│       ├── tools.py       # Tool registry and execution
│       └── ssh_tools.py   # SSH-based discovery tools
├── tests/
│   ├── integration/       # Integration tests (require Docker)
│   │   ├── __init__.py
│   │   ├── conftest.py    # Test fixtures and setup
│   │   └── test_ssh_integration.py
│   ├── test_server.py     # Server unit tests
│   ├── test_tools.py      # Tool unit tests
│   └── test_ssh_tools.py  # SSH tool unit tests
├── docker/
│   └── test-ubuntu/       # Docker setup for integration tests
│       └── Dockerfile
├── scripts/
│   └── run-integration-tests.sh  # Integration test runner
├── docker-compose.test.yml       # Test container orchestration
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies
├── pytest.ini            # Pytest configuration
└── run_server.py         # Entry point
```

### Running Tests

#### Unit Tests
```bash
# Run all unit tests (fast, no Docker required)
pytest tests/ -m "not integration"

# Run with coverage
pytest tests/ -m "not integration" --cov=src/homelab_mcp

# Run specific test file
pytest tests/test_server.py
```

#### Integration Tests
```bash
# Prerequisites: Docker and docker-compose must be installed and running

# Run integration tests (requires Docker)
./scripts/run-integration-tests.sh

# Or run manually
pytest tests/integration/ -m integration -v

# Run specific integration test
pytest tests/integration/test_ssh_integration.py::TestSSHIntegration::test_full_mcp_admin_setup_workflow -v
```

#### All Tests
```bash
# Run all tests (unit + integration)
pytest

# Note: Integration tests will be skipped if Docker is not available
```

### Adding New Tools

1. Define the tool schema in `src/homelab_mcp/tools.py`:
```python
TOOLS["new_tool"] = {
    "description": "Tool description",
    "inputSchema": {
        "type": "object",
        "properties": {
            # Define parameters
        },
        "required": []
    }
}
```

2. Implement the tool logic in the appropriate module

3. Add the execution case in `execute_tool()` function

4. Write tests for the new tool

## License

MIT License - see LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request