# Installation Requirements for Infrastructure-as-Code Features

## MCP Server Dependencies

The MCP server includes the **controllers** and **state management** for infrastructure tools, but you need to install the actual tools.

### ✅ Already Included in MCP
- **Ansible Python Library**: Included in `pyproject.toml`
- **Python Controllers**: `TerraformManager`, `AnsibleRunner` classes
- **State Storage**: Context management, execution logs
- **Templates**: Terraform modules, Ansible playbooks

### 🔧 Required External Tools

#### 1. Terraform (Required)
```bash
# macOS (Homebrew)
brew install terraform

# Ubuntu/Debian
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update && sudo apt-get install terraform

# Verify installation
terraform --version
```

#### 2. Ansible Command-Line Tools
```bash
# The Python library is included, but you may need CLI tools for advanced features
pip install ansible-core

# Verify installation
ansible --version
```

## Installation Flow

### Option 1: Full Installation
```bash
# 1. Install MCP server
pip install -e .

# 2. Install Terraform
brew install terraform  # or your OS equivalent

# 3. Verify everything works
python test_iac_fixes.py
```

### Option 2: Docker Installation (Future)
```dockerfile
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    ssh \
    && rm -rf /var/lib/apt/lists/*

# Install Terraform
RUN curl -fsSL https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip -o terraform.zip \
    && unzip terraform.zip \
    && mv terraform /usr/local/bin/ \
    && rm terraform.zip

# Install MCP server
COPY . /app
WORKDIR /app
RUN pip install -e .

CMD ["python", "main.py"]
```

## What Happens at Runtime

### VM Creation Flow:
1. **AI calls**: `terraform_create_vm`
2. **MCP TerraformManager**: 
   - Generates Terraform configuration
   - Calls `terraform apply` command
   - Stores state in `terraform/state/`
   - Updates MCP context
3. **Terraform binary**: Actually provisions the VM
4. **Result**: VM created + state tracked in MCP

### Service Deployment Flow:
1. **AI calls**: Ansible tools for service deployment
2. **MCP AnsibleRunner**:
   - Generates Ansible playbook
   - Calls `ansible-playbook` command
   - Stores execution logs
   - Updates MCP context
3. **Ansible binary**: Actually configures the service
4. **Result**: Service deployed + execution tracked in MCP

## Benefits of This Architecture

### ✅ MCP as Orchestrator
- **State Management**: All infrastructure state centralized
- **Context Awareness**: AI knows what's been deployed
- **Audit Trail**: Complete history of changes
- **Templates**: Reusable infrastructure patterns

### ✅ Native Tools for Execution  
- **Reliability**: Use proven Terraform/Ansible implementations
- **Features**: Full access to all tool capabilities
- **Community**: Leverage existing modules and playbooks
- **Performance**: Native binary execution

### ✅ Best of Both Worlds
- **AI Intelligence**: Smart decision making and orchestration
- **Tool Reliability**: Battle-tested infrastructure tools
- **State Consistency**: MCP maintains single source of truth
- **Scalability**: Can add more tools (Pulumi, CDK, etc.)

## Quick Start

```bash
# 1. Check if Terraform is installed
terraform --version

# 2. If not installed:
brew install terraform  # macOS
# OR follow OS-specific instructions above

# 3. Test the integration
python test_iac_fixes.py

# 4. Start MCP server
python main.py
```

The MCP server orchestrates everything, but the actual infrastructure work is done by the native tools for maximum reliability and compatibility.