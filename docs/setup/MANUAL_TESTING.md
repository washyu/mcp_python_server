# Manual Testing Guide with Web UI Chat Client

## 🎯 Purpose

This guide helps you test MCP functions through the web UI chat client interface, simulating real user interactions.

## 🚀 Quick Start for Manual Testing

### 1. Start the MCP Server
```bash
# WebSocket mode (for web UI)
uv run python main.py --transport websocket

# Or stdio mode (for Claude Desktop)
uv run python main.py --transport stdio
```

### 2. Start Mock Proxmox API (Optional)
```bash
# If testing without real Proxmox
cd ../testing/mock-api
docker-compose up -d
```

### 3. Open Web UI Chat Client
- Navigate to your web UI chat client
- Connect to MCP server (usually ws://localhost:8765)
- Start testing MCP tools through natural language

## 📋 Manual Test Scenarios

### Infrastructure Discovery Tests
```
User: "Show me all VMs"
Expected: List of VMs with details

User: "Find MySQL servers"  
Expected: Filtered list of MySQL VMs

User: "Show running Ubuntu servers"
Expected: VMs with status=running and OS containing Ubuntu

User: "Discover hardware on proxmox node"
Expected: CPU, Memory, GPU details
```

### AI-Powered Suggestions
```
User: "Suggest deployment for AI training workload"
Expected: Recommends node with GPU (MI50)

User: "Where should I deploy a database server?"
Expected: Recommends node with fast storage, sufficient memory

User: "Optimize VM placement"
Expected: Analysis of current placement with recommendations
```

### Infrastructure Visualization  
```
User: "Generate infrastructure diagram"
Expected: ASCII diagram showing nodes, VMs, resources

User: "Show resource utilization"
Expected: CPU/Memory usage charts

User: "Visualize GPU allocation"
Expected: Which VMs use which GPUs
```

### VM Management (Future)
```
User: "Create a new Ubuntu VM with 4GB RAM"
Expected: VM creation workflow

User: "Clone VM 203 as test-server"
Expected: Cloning process

User: "Start/stop VM 100"
Expected: VM state change
```

### Wizard Workflows
```
User: "Setup Proxmox connection"
Expected: Wizard starts with prompts for:
  - Proxmox host/IP
  - Username
  - Password or API token
  - Test connection option
  - Save credentials option

User: "Create new VM"
Expected: Multi-step wizard:
  - VM name
  - Resource allocation (CPU, RAM, disk)
  - Network configuration
  - Template selection
  - Confirmation step

User: "Configure Ollama"
Expected: Wizard for:
  - Ollama host URL
  - Model selection
  - Test connection
  - Performance settings

User: "Setup new profile"
Expected: Profile wizard:
  - Profile name (dev/prod/staging)
  - Environment settings
  - Service endpoints
  - Credential configuration
```

## 🧪 Integration Test Mapping

Map failed integration tests to manual test scenarios:

### Failed: `test_websocket_integration.py`
**Manual Test**: 
1. Connect web UI to WebSocket server
2. Send tool discovery request
3. Execute a tool through chat
4. Verify response format

### Failed: `test_wizard_integration.py`
**Manual Test**:
1. Type "Setup Proxmox connection" in chat
2. Follow wizard prompts:
   - Enter Proxmox IP: 192.168.10.200
   - Enter username: root@pam
   - Enter password or token
   - Choose "Test connection"
   - Confirm to save credentials
3. Verify connection success message
4. Check credentials are saved (try "list VMs")

**Wizard Edge Cases to Test**:
- Cancel wizard mid-flow
- Enter invalid IP/credentials
- Test with API token vs password
- Switch between profiles during wizard

### Failed: `test_proxmox_integration.py`
**Manual Test**:
1. Query Proxmox resources through chat
2. Test with both mock and real Proxmox
3. Verify data accuracy

## 📊 Manual Testing Checklist

### Basic Connectivity
- [ ] Web UI connects to MCP WebSocket server
- [ ] Tool list is retrieved successfully  
- [ ] Basic tool execution works

### Discovery Tools
- [ ] `list_nodes` returns node information
- [ ] `list_vms` returns VM list
- [ ] `discover_hardware` shows GPUs/CPUs
- [ ] Natural language filtering works

### AI Features  
- [ ] Deployment suggestions are sensible
- [ ] GPU workloads prefer GPU nodes
- [ ] Resource constraints are respected

### Visualization
- [ ] Infrastructure diagrams generate
- [ ] ASCII art is properly formatted
- [ ] Resource bars show correctly

### Error Handling
- [ ] Graceful handling of offline services
- [ ] Clear error messages for users
- [ ] Recovery suggestions provided

## 🔧 Debugging Manual Tests

### Enable Debug Logging
```bash
# In your .env
DEBUG=true
LOG_LEVEL=DEBUG

# Start server with verbose output
uv run python main.py --transport websocket --debug
```

### Check Server Logs
- Watch terminal for incoming requests
- Verify tool execution flow
- Check for Python exceptions

### Web UI Console
- Open browser developer tools
- Check Network tab for WebSocket messages
- Look for JavaScript errors

## 🎭 Test Environments

### Local Development
```bash
# Everything on dev machine
OLLAMA_HOST=http://localhost:11434
PROXMOX_HOST=http://localhost:8080  # Mock API
```

### Integration Testing
```bash
# Using real services
OLLAMA_HOST=http://192.168.10.185:11434  # Pi5
PROXMOX_HOST=http://192.168.10.200:8006  # Real Proxmox
```

### Demo Mode
```bash
# Best performance, real services
OLLAMA_HOST=http://192.168.10.185:11434
PROXMOX_HOST=http://192.168.10.200:8006
# Use production models and full features
```

## 📝 Recording Manual Test Results

### Success Template
```
Test: [Scenario name]
Input: [What you typed in chat]
Expected: [What should happen]
Actual: [What actually happened]
Status: ✅ PASS
```

### Failure Template  
```
Test: [Scenario name]
Input: [What you typed in chat]
Expected: [What should happen]
Actual: [What actually happened]
Status: ❌ FAIL
Error: [Error message or unexpected behavior]
Server Log: [Relevant log entries]
```

## 🚀 Continuous Improvement

1. **Convert successful manual tests** to automated tests
2. **Document edge cases** discovered during manual testing
3. **Create regression tests** for bugs found
4. **Update integration tests** based on real usage patterns

## 💡 Tips for Effective Manual Testing

1. **Start simple**: Test basic tool discovery first
2. **Build complexity**: Move to advanced queries gradually
3. **Test edge cases**: Try nonsensical queries, typos
4. **Verify consistency**: Run same query multiple times
5. **Check performance**: Note response times
6. **Test failures**: Disconnect services, bad inputs

Remember: Manual testing through the web UI chat client is **invaluable** for understanding the real user experience!