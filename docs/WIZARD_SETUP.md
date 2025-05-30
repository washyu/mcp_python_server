# MCP Wizard Setup Guide

The MCP server includes interactive wizard functionality for collecting Proxmox configuration data through a conversational interface.

## Overview

The wizard system provides:

1. **SimpleSetup** - Streamlined configuration wizard for your Proxmox server
2. **WizardFlow** - Chat-based wizard framework integrated with the AI agent
3. **ProfileManager** - Backend storage (currently used for single server, extensible for future multi-server support)

## Features

### SetupWizard
- Interactive terminal-based configuration collection
- Automatic .env file generation
- Configuration validation
- Backup of existing configurations
- Password masking for sensitive data
- Section-based configuration (Proxmox, Ollama, Ansible, etc.)

### WizardFlow
- Define custom wizard flows with steps
- Input validation at each step
- Support for different input types (text, password, choices)
- Default values and options
- Easy integration with chat interfaces

### SimpleSetup (Recommended)
- Streamlined single-server configuration
- Automatic detection of existing configuration
- Saves to both profile and .env file
- Includes VM template settings
- Clear, step-by-step process

## Usage Examples

### 1. Running the Simple Setup (Recommended)

```bash
# Run the simple setup wizard
uv run python -m src.utils.simple_setup

# This will:
# - Check for existing configuration
# - Collect Proxmox connection details
# - Configure VM template settings
# - Save everything to .env
```

### 2. Using the Chat-Based Wizard Agent

```bash
# Start the WebSocket server
uv run python main.py --transport websocket

# In another terminal, run the wizard agent
uv run python src/agents/websocket_wizard_agent.py
```

Then in the chat:
- Type `setup proxmox` to configure your Proxmox connection
- Type `show config` to see current Proxmox settings
- Type `create vm` to start VM creation wizard

### 3. Creating Custom Wizard Flows

```python
from src.utils.setup_wizard import WizardFlow

# Create wizard instance
wizard = WizardFlow()

# Define your flow
steps = [
    {
        "key": "service_name",
        "prompt": "What service would you like to install?",
        "options": ["jenkins", "gitlab", "nextcloud"],
        "validator": lambda x: (True, "") if x else (False, "Service name required")
    },
    {
        "key": "vm_name", 
        "prompt": "What should we name the VM?",
        "default": "my-service-vm"
    }
]

wizard.define_flow("service_setup", steps)

# Use in your agent
step = wizard.start_flow("service_setup")
# ... handle user responses
```

## Wizard Flow Structure

Each wizard step can have:
- `key` - Unique identifier for storing the response
- `prompt` - Question to ask the user
- `default` - Default value if user presses enter
- `options` - List of valid choices
- `input_type` - Type of input (text, password)
- `validator` - Function to validate responses

## Built-in Wizards

### Proxmox Setup Wizard
Collects:
- Proxmox host/IP
- Username (with realm validation)
- Password (masked input)
- SSL verification preference
- Template VM configuration

### VM Creation Wizard
Collects:
- VM name
- VM type (web-server, database, dev-environment)
- VM size (small, medium, large with resource mapping)

## Testing Wizards

```bash
# Test wizard components
uv run python examples/test_wizard.py

# Test with the WebSocket agent
uv run python src/agents/websocket_wizard_agent.py
```

## Integration with MCP Tools

The wizard results can be directly passed to MCP tools:

```python
# After wizard completion
if wizard_name == "proxmox_setup":
    # Save configuration
    save_to_env(data)
    
    # Test connection
    result = await mcp_client.call_tool("test_proxmox_connection", data)

elif wizard_name == "vm_creation":
    # Create VM with collected data
    result = await mcp_client.call_tool("create_vm", {
        "name": data["vm_name"],
        "template": "ubuntu-cloud-template",
        **resource_mapping[data["vm_size"]]
    })
```

## Extending the Wizard System

1. **Add new configuration sections** to SetupWizard
2. **Create custom flows** for specific workflows
3. **Add validation functions** for complex requirements
4. **Integrate with MCP tools** for immediate actions
5. **Store wizard history** for repeated operations

## Best Practices

1. Always validate user input
2. Provide sensible defaults
3. Mask sensitive information
4. Offer to backup existing configurations
5. Test connections after configuration
6. Provide clear error messages
7. Allow users to exit gracefully

## How Configuration Works

### Initial Setup

When you first run the wizard, it will:

1. Ask for your Proxmox server details (IP: 192.168.10.200)
2. Collect credentials (username/password)
3. Configure VM template settings (ID: 9000)
4. Save everything to `.env` and `profiles/profiles.json`

### Configuration Storage

Your configuration is stored in two places:
- `.env` file - Used by the MCP server at runtime
- `profiles/profiles.json` - Backup storage for the wizard

### Viewing Configuration

In the chat agent, type `show config` to see:
```
Current Proxmox Configuration:
  Host: 192.168.10.200
  User: root@pam
  Password: ********
  Verify SSL: false

✓ Configuration is active
```

### Reconfiguring

If you need to change settings (e.g., update password):
1. Run `setup proxmox` again in the chat
2. The wizard will show existing settings as defaults
3. Update only what needs changing
4. Configuration is automatically saved

## Future Enhancements

- [ ] Connection testing after setup
- [ ] Auto-discovery of VM templates
- [ ] Backup/restore configuration
- [ ] Encrypted credential storage
- [ ] Multi-server support (when needed)
- [ ] Integration with credential vaults