# Ansible MCP Server - Project Context

## 🎯 MVP Definition: Universal Homelab MCP Server

**Core Vision**: This MCP server provides tools and context for AI agents to intelligently manage homelab infrastructure. The AI agent makes decisions based on user requirements and available resources discovered through the MCP.

### Key MVP Requirements:
1. **Context-Aware Infrastructure Discovery**
   - MCP provides tools to discover ALL Proxmox resources (nodes, VMs, storage, networks)
   - Maintains up-to-date inventory of hardware capabilities and current usage
   - AI agents use this context to make informed decisions
   - Regular inventory refresh to ensure accurate state

2. **AI Decision Making**
   - AI agent analyzes user requirements against available resources
   - Makes intelligent choices about VM sizing, node placement, storage allocation
   - Considers current cluster utilization before provisioning
   - Provides recommendations and alternatives when resources are constrained

3. **Tool-Based Operations**
   - MCP provides tools, NOT automation logic
   - AI agent orchestrates tool usage based on context and requirements
   - Clear separation: MCP = tools + context, AI = decision making
   - Universal interface that any MCP-compatible AI can use

4. **Workflow Example**
   - User: "I need a Jenkins server"
   - AI Agent:
     1. Uses MCP to discover current cluster state
     2. Analyzes available resources (CPU, memory, storage)
     3. Determines optimal VM configuration and placement
     4. Uses MCP tools to create and configure the VM
     5. Monitors deployment and adjusts as needed

### Core MCP Components:
1. **Discovery Tools** - Inventory ALL infrastructure:
   - Proxmox cluster resources (VMs, storage, networks)
   - Bare metal servers (via Ansible inventory)
   - External services (Pi-hole, NAS, mail servers)
   - Network devices (routers, switches, bridges)
   - Security posture (open ports, vulnerabilities)

2. **Execution Tools** - Manage hybrid infrastructure:
   - Ansible for bare metal and VM configuration
   - Terraform for VM provisioning
   - Direct API calls for network devices
   - Security scanning integration

3. **Template Library** - Complete infrastructure templates:
   - VM creation (provider-agnostic)
   - Bare metal server configuration
   - Network device setup (routers, bridges)
   - Security hardening playbooks
   - External service deployment (Pi-hole, mail, NAS)

4. **Standard Operating Procedures (SOPs)** - Holistic operations:
   - Infrastructure operations (VMs AND bare metal)
   - Network topology management
   - Security scanning and remediation
   - Failover and redundancy setup
   - Service distribution for resilience

5. **Security Tools** - Continuous security monitoring:
   - Port scanning (nmap integration)
   - Vulnerability scanning
   - Configuration compliance
   - SSL certificate management
   - Access audit logs

### Template Categories:
- **Infrastructure Templates** (Terraform)
  - Create VM with specific resources (`terraform/modules/compute/`)
  - Configure networking and storage (`terraform/modules/network/`)
  - Set up GPU passthrough (`terraform/ollama-gpu-vm/`)
  - Clone from templates (`playbooks/create-vm.yml`)
  
- **Service Templates** (Ansible)
  - Install and configure Jenkins (`playbooks/install-jenkins.yml`)
  - Deploy Ollama with GPU (`playbooks/install-ollama.yml`, `playbooks/configure-ollama-gpu.yml`)
  - WordPress + MySQL + SSL (`playbooks/deploy-wordpress.yml`)
  - Plex/Jellyfin media server (`playbooks/deploy-media-server.yml`)
  - Home Assistant (`playbooks/deploy-home-assistant.yml`)
  - Cloudflare tunnel (`playbooks/setup-cloudflare-tunnel.yml`)
  - Set up monitoring (Prometheus/Grafana)
  - Configure backup solutions
  
- **Configuration Templates** (Ansible)
  - Modify service settings
  - Update Proxmox configurations
  - Manage users and permissions (`playbooks/setup-ollama-ssh.yml`)
  - Configure SSL certificates

### MCP Template Tools:
- `list-templates` - Show available templates by category
- `get-template` - Retrieve a specific template with parameters
- `generate-from-template` - Create customized script from template
- `validate-template` - Check if template is valid for current environment

### SOP System:
**Basic Operations SOPs** (Built into MCP):
- VM Creation: Steps, resource requirements, validation checks
- Network Configuration: VLAN setup, firewall rules, IP allocation
- Storage Management: Disk creation, expansion, backup procedures
- User Management: SSH keys, permissions, access control

**Service-Specific SOPs** (Dynamic):
- Query target VM OS/architecture
- Determine correct binaries/packages
- Provide installation steps adapted to environment
- Include post-installation validation
- Example: Installing Jenkins
  - Detect OS (Ubuntu 22.04, CentOS 8, etc.)
  - Select appropriate Java version
  - Choose Jenkins package for architecture
  - Configure based on available resources

### MCP SOP Tools:
- `query-sop` - Get SOP for specific operation
- `list-sops` - Show all available SOPs
- `get-service-requirements` - Check prerequisites for service installation
- `validate-environment` - Verify environment meets SOP requirements

### How SOPs Guide AI Agents:
1. **User Request**: "Install Jenkins"
2. **AI Agent Workflow**:
   - Query SOP for "install_jenkins"
   - Check prerequisites (Java, memory requirements)
   - Discover existing Jenkins instances
   - Determine target VM OS/architecture
   - Select appropriate installation method
   - Generate customized playbook from templates
   - Execute installation with validation steps
   - Update context with new service details

### What This Means:
- MCP provides: Tools, context, templates, AND procedural knowledge (SOPs)
- AI provides: Intelligence to interpret SOPs, make decisions, and adapt to environment
- Together: User gets intelligent infrastructure automation that follows best practices

## Architecture Principles
1. **Provider-Agnostic Design**
   - All configurations (VM, network, storage) use provider-agnostic format
   - "Driver" pattern converts agnostic configs to provider-specific implementations
   - Current driver: Proxmox (future: AWS, GCP, Azure, VMware)
   - AI agents work with abstract resources, not provider-specific details

### Provider Driver Architecture:
```
User Request → AI Agent → Agnostic Config → Provider Driver → Provider API
                   ↓                              ↓
              (decisions)                   (translation)
                   ↓                              ↓
              Inventory ←  Validation  ←  Implementation
```

### Agnostic Configuration Example:
```json
{
  "resource_type": "compute",
  "name": "jenkins-server",
  "specs": {
    "cpu": 4,
    "memory_gb": 8,
    "storage_gb": 50,
    "network": "default",
    "os": "ubuntu-22.04"
  }
}
```

### Provider Drivers Translate To:
- **Proxmox**: `qm create`, specific template IDs, network bridges
- **AWS**: EC2 instance types, AMIs, VPCs
- **GCP**: Compute Engine, machine types, images
- **Azure**: VM sizes, marketplace images, VNets

2. **OS Configuration via Ansible**
   - Use Ansible for ALL OS-level configuration and application deployment
   - Keeps configuration portable across different infrastructure providers
   - Separation of concerns: Terraform = Infrastructure, Ansible = Configuration

3. **Provider Preferences**
   - For Proxmox: Use `bpg/proxmox` provider (more stable than Telmate)
   - Always test with multiple providers when adding new features

## Infrastructure Constraints
- **Proxmox Development Environment**:
  - Max 12 vCPUs per VM (host limitation)
  - Node name: "proxmox" (not "pve")
  - Template ID 9000: ubuntu-cloud-template

## MCP Server Deployment
- **Dev MCP Server**: 192.168.10.102 (for testing)
- **Production MCP Server**: 192.168.10.110
- **Current Dev VM**: 192.168.10.169 (VM ID 100 on Proxmox)
- **Proxmox Host**: 192.168.10.200

**IMPORTANT**: When testing MCP features, use the dev MCP server at 192.168.10.102, NOT local installations!

## 🗄️ CRITICAL: Inventory Context System (January 25, 2025)
**PRIORITY**: The MCP MUST maintain up-to-date inventory context of all infrastructure resources.

### Core Requirements:
1. **Complete Proxmox Inventory**: VMs, templates, ISOs, storage pools, nodes, networks
2. **Automatic Staleness Detection**: Context expires after configurable time (default: 10 hours)
3. **Background Refresh**: Auto-update stale inventory in background
4. **Tool Blocking**: Block infrastructure tools during inventory refresh to prevent inconsistent state
5. **State Modification Tracking**: All create/modify/delete operations MUST update inventory context immediately

### Implementation Plan:
- Add Proxmox discovery tool to scan: VMs, templates (ID 9000), ISOs, storage, networks
- Create inventory refresh mechanism with configurable staleness threshold
- Implement tool blocking during refresh operations
- Add inventory update hooks to all state-modifying tools
- Store inventory with timestamps in `/inventory/proxmox-resources.json`

### Template VM Management Requirements:
1. **Create Templates**: MCP should be able to create new VM templates with:
   - Pre-configured SSH keys from MCP server
   - Cloud-init ready configuration
   - Standard user accounts and passwords
2. **Store Template Context**: When creating templates, store:
   - Template ID, name, and configuration
   - SSH access credentials
   - Cloud-init settings
   - Default user accounts
3. **Template Discovery**: Automatically discover and catalog existing templates
4. **Clone Configuration**: Store successful clone configurations as reusable templates

### Context Files That Need This:
- `/inventory/proxmox-resources.json` - Complete Proxmox resource inventory
- `/inventory/last-discovery.json` - Discovery timestamps and metadata
- `.env` - Staleness threshold configuration (`INVENTORY_STALENESS_HOURS=10`)

**This is BLOCKING for VM creation - we need to know about template 9000 and all available resources before any infrastructure operations.**

## 📦 State Management (MVP)
- **Context Storage**: All state stored in `/inventory/` directory
- **Periodic Refresh**: Automatic scans update context every 10 hours
- **Validation**: Compare discovered state vs stored playbook inventory
- **Backup**: Basic ZIP export of entire context for download
- **Credentials**: Stored in `.env` files (user-editable)

## 🔮 Post-MVP Features (Documented)
1. **MCP High Availability** - Redundant MCP servers
2. **Advanced Credential Management** - Vault integration
3. **Audit Logging** - Important for multi-provider compliance
4. **Rate Limiting** - Prevent resource exhaustion
5. **Security Scanning** - Full nmap, vulnerability assessment
6. **Bare Metal Discovery** - Auto-discover physical servers
7. **Multi-Provider Support** - AWS, GCP, Azure drivers

## 📚 Standard Operating Procedures (SOPs)
The MCP now includes built-in SOPs for common operations. AI agents can query these using:
- `query-sop` - Get detailed steps for any operation (e.g., "create_vm", "install_ollama")
- `list-sops` - List all available procedures
- `get-best-practice` - Get naming conventions, resource allocation guidelines
- `get-error-recovery` - Get recovery steps for common errors

### Example SOP Usage:
```
query-sop operation="create_vm" detailed=true
```

This provides agents with:
1. Step-by-step instructions
2. Validation checks at each step
3. Common issues and solutions
4. Prerequisites and requirements

## 🔐 Ansible Admin Account Management
**CRITICAL**: All VMs created by MCP now include a standard `ansible-admin` account for consistent access.

### Default Configuration:
- **Username**: `ansible-admin`
- **Access**: Full sudo without password (NOPASSWD)
- **SSH Keys**: MCP's SSH key automatically added
- **Password**: Auto-generated 20-char secure password, encrypted in context

### Credential Management Tools:
- `store-vm-credentials` - Store VM credentials after creation
- `retrieve-vm-credentials` - Get credentials (with optional decryption)
- `generate-secure-password` - Generate passwords for accounts
- `update-context-after-operation` - Update context after any operation
- `list-vm-credentials` - List all VMs with their access info

### Automatic Context Updates:
Every successful operation now updates the MCP context:
- VM creation → Stores IP, credentials, resources, purpose
- Service installation → Stores endpoints, versions, config
- All credentials encrypted and vaulted

### Example:
```bash
# After VM creation
store-vm-credentials vmId="203" vmName="ollama-server" vmIp="192.168.10.203"

# Retrieve credentials later
retrieve-vm-credentials vmId="203" decrypt=true

# Update context after service install
update-context-after-operation operationType="service_installed" entityId="ollama" updates={endpoint:"http://192.168.10.203:11434", version:"0.1.17"}
```

## 🎯 Modular Service SOPs
The MCP now uses a modular service SOP system to avoid duplication:

### Service SOP Structure:
- **Base SOP** (`/src/service-sops/base-service-sop.json`) - Common steps for all services
- **Service-Specific SOPs** (`/src/service-sops/{service}-sop.json`) - Service-specific details

### Available Service SOPs:
- `ollama` - LLM inference server
- `nextcloud` - Self-hosted cloud storage
- `docker` - Container runtime
- More can be added without changing core code

### Service SOP Tools:
- `get-service-sop` - Get complete SOP for any service
- `list-service-sops` - List all available service SOPs
- `compare-service-requirements` - Compare resource needs across services

### Example Usage:
```bash
# Get Ollama installation SOP
get-service-sop serviceName="ollama" section="installation"

# Compare requirements for multiple services
compare-service-requirements services=["ollama", "nextcloud"]

# Check if service already exists
detect-existing-service serviceName="nextcloud"
```

## 📋 Template Validation & Compliance
All templates MUST have `ansible-admin` account pre-configured for MCP management.

### Template Requirements:
- **ansible-admin** user with sudo NOPASSWD
- MCP SSH keys in authorized_keys
- cloud-init installed and configured
- Python3, sudo, openssh-server packages

### Template Validation Tools:
- `validate-template` - Check if template meets MCP standards
- `fix-template` - Fix non-compliant templates (add ansible-admin, etc.)
- `discover-templates` - Find and validate all templates
- `create-compliant-template` - Create new MCP-compliant template

### Template Discovery Workflow:
1. **Unknown Template Found** → Alert user
2. **Validation Options**:
   - Validate: Test ansible-admin access
   - Fix: Add ansible-admin if missing
   - Delete: Remove if not needed
   - Keep: Mark as legacy/non-compliant

### Example:
```bash
# Discover all templates
discover-templates validateAll=true

# Validate specific template
validate-template templateId="9001"

# Fix non-compliant template
fix-template templateId="9001" issue="no_ansible_admin" action="fix" credentials={username:"root", password:"..."}
```

## 🔍 Inventory Deviation Management
The MCP now includes advanced inventory deviation detection:

### Deviation Detection Tools:
- `compare-inventory-state` - Compare context vs live inventory, detect new/missing VMs
- `process-deviation` - Handle deviations (accept new VMs, restore missing ones)
- `check-node-capacity` - Verify node has resources for VM placement
- `find-best-node` - Find optimal node for new VM based on resources

### Key Features:
1. **Automatic Deviation Detection**:
   - New VMs trigger alerts asking if expected
   - Missing VMs offer recovery options (backup/terraform/ansible)
   - Resource changes are tracked

2. **Resource Tracking**:
   - Each node's CPU/memory/storage limits and usage
   - Automatic alerts at 80% (warning) and 90% (critical)
   - VM placement validation before creation

3. **Alert Templates**:
   - New VM: Asks for purpose, owner, credentials
   - Missing VM: Offers restore from backup/IaC
   - Resource exhaustion: Prevents new VMs, suggests actions

### Example Workflow:
```
# Check for deviations
compare-inventory-state autoAlert=true updateContext=true

# If new VM found
process-deviation deviationType="new_vm" vmId="203" action="accept" details={purpose:"Test server", owner:"DevOps"}

# Check where to place new VM
find-best-node requiredResources={cores:4, memoryMb:8192, diskGb:100}
```

## Development Philosophy

### Linux-First Approach
- **MVP Focus**: Full Linux/Unix support for homelab environments
- **Target Environment**: Proxmox VE (Debian-based) and Ubuntu VMs
- **Development Platform**: Linux/WSL2
- **Deployment**: Linux containers and VMs
- **Windows/macOS**: Post-MVP consideration

This aligns with typical homelab infrastructure where:
- Proxmox runs on Linux
- Most VMs are Linux-based
- Ansible works natively on Linux
- Container workloads are Linux-based

## Current Status (January 28, 2025)

### 🐍 Python Migration
1. **Language Migration**
   - Migrating project from Node.js/JavaScript to Python
   - Using modern Python tooling (uv for package management)
   - Implementing MCP server using Python MCP SDK
   - Focus on type safety and async/await patterns

2. **GitHub Repository**
   - Pushed all changes to main branch (not master)
   - Removed accidentally committed .claude folder
   - Added .claude/ to .gitignore for security
   - Created 20 comprehensive GitHub issues for TODOs and features

3. **Community Engagement**
   - Created CONTRIBUTING.md with contribution guidelines
   - Drafted 3 LinkedIn post options for first-time posting
   - Prepared community feedback strategies

### 📋 Next Priority: Core MCP Tools (Linux)

1. **Proxmox Discovery Tool** - List VMs, templates, storage, networks
2. **Ansible Execution Tool** - Run playbooks on Linux hosts
3. **VM Creation Tool** - Create VMs from template 9000
4. **Inventory Manager** - Track infrastructure state
5. **Basic Tests** - Pytest suite for Linux environment

### 🔧 CI/CD Implementation Plan

#### 1. GitHub Actions Workflow (Python)
Create `.github/workflows/ci.yml`:
```yaml
name: CI/CD Pipeline
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: uv sync
      - name: Run tests
        run: uv run pytest
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: coverage-report
          path: htmlcov/

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - uses: docker/setup-buildx-action@v2
      - uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_TOKEN }}
      - uses: docker/build-push-action@v4
        with:
          push: true
          tags: |
            yourusername/ansible-mcp-server:latest
            yourusername/ansible-mcp-server:${{ github.sha }}
```

#### 2. Dockerfile for Python
Create a production-ready Dockerfile:
```dockerfile
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ansible \
    openssh-client \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy project files
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 3000
CMD ["uv", "run", "python", "main.py"]
```

#### 3. Docker Compose for Local Testing
```yaml
version: '3.8'
services:
  ansible-mcp:
    build: .
    volumes:
      - ./ansible:/ansible
      - ~/.ssh:/root/.ssh:ro
    environment:
      - ANSIBLE_HOST_KEY_CHECKING=False
```

### 🧪 Python Testing Strategy
- Test framework: pytest
- Async testing: pytest-asyncio
- Mocking: unittest.mock and pytest-mock
- Coverage: pytest-cov
- Type checking: mypy
- Linting: ruff

### 🚀 MVP Priority Features (Linux-First)
1. **Core MCP Implementation** - Get basic Proxmox/Ansible tools working on Linux
2. **Inventory Discovery** - Auto-discover Proxmox resources
3. **Template Management** - VM creation from templates
4. **Basic Testing** - Ensure core functionality works on Linux
5. **WebSocket + Stdio Transports** - Support for various AI clients

## 📦 Post-MVP Features
1. **GitHub Repository Deployment**
   - Deploy applications directly from GitHub repos
   - Support for docker-compose, Ansible playbooks, Terraform configs
   - Auto-detect deployment type from repo structure
   - Clone → Configure → Deploy workflow
   - Example: `deploy-from-github repo="user/awesome-app" vm="web-server"`

2. **Transport Wrappers**
   - Proxmox addon wrapper
   - OpenAI/Anthropic API compatibility
   - Home Assistant integration
   - CLI wrapper for terminal use

3. **Cross-Platform Support**
   - Windows support for Ansible execution
   - macOS compatibility
   - Platform-specific adaptations

### 📝 Important Notes
- Using uv for fast, reliable Python package management
- Python 3.11+ for modern async/await and type hints
- Main branch, not master
- Don't commit .claude folder (contains permissions)
- Follow PEP 8 and use type hints throughout

### 🔍 Key Files to Remember
- `/pyproject.toml` - Python project configuration
- `/main.py` - MCP server entry point
- `/tools/` - MCP tool implementations
- `/utils/` - Shared utilities
- `/.gitignore` - Includes .claude/
- `/uv.lock` - Locked dependencies

### 💡 Next Tasks
1. Implement core MCP server structure in Python
2. Create discovery tools for Proxmox inventory
3. Implement execution tools with Ansible integration
4. Set up pytest test suite
5. Create Python-based CI/CD pipeline
6. Document Python implementation decisions

### 🔐 Security Reminders
- Never commit .claude folder
- Use GitHub secrets for Docker Hub credentials
- Consider separate permissions for CI/CD
- Review Ansible vault setup for sensitive data

---

**Current Focus**: Migrating Ansible MCP Server from Node.js/JavaScript to Python for better integration with infrastructure tools and improved performance.