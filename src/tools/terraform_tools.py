"""Terraform integration tools for infrastructure provisioning."""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.types import Tool, TextContent

from ..utils.config import Config
from ..utils.homelab_context import HomelabContextManager


class TerraformManager:
    """Manages Terraform operations for infrastructure provisioning."""
    
    def __init__(self):
        self.terraform_dir = Path(__file__).parent.parent.parent / "terraform"
        self.state_dir = Path(__file__).parent.parent.parent / "terraform" / "state"
        self.modules_dir = self.terraform_dir / "modules"
        self.context_manager = HomelabContextManager()
        
        # Ensure directories exist
        self.state_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_vm_with_terraform(
        self,
        vm_name: str,
        target_node: str,
        cpu_cores: int = 2,
        memory_gb: int = 2,
        disk_size_gb: int = 20,
        template_id: int = 9000,
        ssh_keys: Optional[List[str]] = None,
        vm_tags: Optional[List[str]] = None,
        start_vm: bool = True
    ) -> Dict[str, Any]:
        """Create a VM using Terraform."""
        
        # Generate Terraform configuration
        config_dir = self.state_dir / f"vm-{vm_name}"
        config_dir.mkdir(exist_ok=True)
        
        # Create main.tf for this VM
        main_tf_content = self._generate_vm_terraform_config(
            vm_name=vm_name,
            target_node=target_node,
            cpu_cores=cpu_cores,
            memory_gb=memory_gb,
            disk_size_gb=disk_size_gb,
            template_id=template_id,
            ssh_keys=ssh_keys or [],
            vm_tags=vm_tags or ["mcp-managed", "homelab"],
            start_vm=start_vm
        )
        
        # Write Terraform configuration
        main_tf_path = config_dir / "main.tf"
        main_tf_path.write_text(main_tf_content)
        
        # Write terraform.tfvars
        tfvars_content = self._generate_tfvars(
            vm_name=vm_name,
            target_node=target_node,
            cpu_cores=cpu_cores,
            memory_gb=memory_gb,
            disk_size_gb=disk_size_gb,
            template_id=template_id,
            ssh_keys=ssh_keys or [],
            vm_tags=vm_tags or ["mcp-managed", "homelab"],
            start_vm=start_vm
        )
        
        tfvars_path = config_dir / "terraform.tfvars"
        tfvars_path.write_text(tfvars_content)
        
        try:
            # Initialize Terraform
            await self._run_terraform_command(["init"], cwd=config_dir)
            
            # Plan
            plan_result = await self._run_terraform_command(
                ["plan", "-out=terraform.tfplan"], cwd=config_dir
            )
            
            # Apply
            apply_result = await self._run_terraform_command(
                ["apply", "-auto-approve", "terraform.tfplan"], cwd=config_dir
            )
            
            # Get outputs
            outputs = await self._get_terraform_outputs(config_dir)
            
            # Store state in context
            await self._store_terraform_context(vm_name, config_dir, outputs)
            
            return {
                "success": True,
                "vm_name": vm_name,
                "vm_id": outputs.get("vm_id", {}).get("value"),
                "node_name": outputs.get("node_name", {}).get("value"),
                "terraform_state_dir": str(config_dir),
                "outputs": outputs,
                "plan_output": plan_result.get("stdout", ""),
                "apply_output": apply_result.get("stdout", "")
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "vm_name": vm_name,
                "terraform_state_dir": str(config_dir)
            }
    
    def _generate_vm_terraform_config(
        self,
        vm_name: str,
        target_node: str,
        cpu_cores: int,
        memory_gb: int,
        disk_size_gb: int,
        template_id: int,
        ssh_keys: List[str],
        vm_tags: List[str],
        start_vm: bool
    ) -> str:
        """Generate Terraform configuration for VM creation."""
        
        # Get Proxmox credentials from config
        proxmox_config = Config.get_proxmox_config()
        
        return f'''terraform {{
  required_providers {{
    proxmox = {{
      source  = "bpg/proxmox"
      version = "~> 0.66.0"
    }}
  }}
}}

provider "proxmox" {{
  endpoint = "{proxmox_config.get('host', 'https://192.168.10.200:8006')}"
  username = "{proxmox_config.get('username', 'root@pam')}"
  password = "{proxmox_config.get('password', '')}"
  insecure = true
}}

module "vm" {{
  source = "../../modules/proxmox-vm"
  
  vm_name                = var.vm_name
  vm_description         = var.vm_description
  vm_tags               = var.vm_tags
  target_node           = var.target_node
  template_id           = var.template_id
  cpu_cores             = var.cpu_cores
  memory_mb             = var.memory_mb
  disks                 = var.disks
  ssh_keys              = var.ssh_keys
  cloud_init_password   = var.cloud_init_password
  start_vm              = var.start_vm
}}

output "vm_id" {{
  value = module.vm.vm_id
}}

output "vm_name" {{
  value = module.vm.vm_name
}}

output "node_name" {{
  value = module.vm.node_name
}}

output "vm_tags" {{
  value = module.vm.vm_tags
}}

output "vm_resource" {{
  value = module.vm.vm_resource
}}
'''
    
    def _generate_tfvars(
        self,
        vm_name: str,
        target_node: str,
        cpu_cores: int,
        memory_gb: int,
        disk_size_gb: int,
        template_id: int,
        ssh_keys: List[str],
        vm_tags: List[str],
        start_vm: bool
    ) -> str:
        """Generate terraform.tfvars file."""
        
        ssh_keys_str = '[\n  ' + ',\n  '.join(f'"{key}"' for key in ssh_keys) + '\n]' if ssh_keys else '[]'
        vm_tags_str = '[\n  ' + ',\n  '.join(f'"{tag}"' for tag in vm_tags) + '\n]'
        
        return f'''vm_name        = "{vm_name}"
vm_description = "VM created by MCP Homelab Server via Terraform"
vm_tags        = {vm_tags_str}
target_node    = "{target_node}"
template_id    = {template_id}
cpu_cores      = {cpu_cores}
memory_mb      = {memory_gb * 1024}
disks = [
  {{
    datastore_id = "local-lvm"
    size_gb      = {disk_size_gb}
    interface    = "scsi0"
    file_format  = "raw"
  }}
]
ssh_keys              = {ssh_keys_str}
cloud_init_password   = "$6$rounds=4096$saltsalt$hash"  # Will be replaced with actual hash
start_vm              = {str(start_vm).lower()}
'''
    
    async def _run_terraform_command(
        self, 
        args: List[str], 
        cwd: Path
    ) -> Dict[str, Any]:
        """Run a Terraform command."""
        
        cmd = ["terraform"] + args
        
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(cmd)
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timed out after 5 minutes",
                "command": " ".join(cmd)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": " ".join(cmd)
            }
    
    async def _get_terraform_outputs(self, config_dir: Path) -> Dict[str, Any]:
        """Get Terraform outputs as JSON."""
        
        result = await self._run_terraform_command(
            ["output", "-json"], cwd=config_dir
        )
        
        if result["success"]:
            try:
                return json.loads(result["stdout"])
            except json.JSONDecodeError:
                return {}
        
        return {}
    
    async def _store_terraform_context(
        self, 
        vm_name: str, 
        config_dir: Path, 
        outputs: Dict[str, Any]
    ) -> None:
        """Store Terraform state information in MCP context."""
        
        terraform_context = {
            "vm_name": vm_name,
            "terraform_state_dir": str(config_dir),
            "terraform_outputs": outputs,
            "provisioner": "terraform",
            "created_at": Config.get_current_timestamp(),
            "state_files": {
                "terraform_state": str(config_dir / "terraform.tfstate"),
                "terraform_plan": str(config_dir / "terraform.tfplan"),
                "main_tf": str(config_dir / "main.tf"),
                "tfvars": str(config_dir / "terraform.tfvars")
            }
        }
        
        # Store in inventory context
        await self.context_manager.update_terraform_context(vm_name, terraform_context)
    
    async def destroy_vm_with_terraform(self, vm_name: str) -> Dict[str, Any]:
        """Destroy a VM using Terraform."""
        
        config_dir = self.state_dir / f"vm-{vm_name}"
        
        if not config_dir.exists():
            return {
                "success": False,
                "error": f"No Terraform state found for VM: {vm_name}"
            }
        
        try:
            # Run terraform destroy
            result = await self._run_terraform_command(
                ["destroy", "-auto-approve"], cwd=config_dir
            )
            
            if result["success"]:
                # Remove Terraform state directory
                import shutil
                shutil.rmtree(config_dir)
                
                # Remove from context
                await self.context_manager.remove_terraform_context(vm_name)
            
            return {
                "success": result["success"],
                "vm_name": vm_name,
                "destroy_output": result.get("stdout", ""),
                "error": result.get("stderr", "") if not result["success"] else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "vm_name": vm_name
            }
    
    async def list_terraform_managed_vms(self) -> List[Dict[str, Any]]:
        """List all VMs managed by Terraform."""
        
        terraform_vms = []
        
        for vm_dir in self.state_dir.iterdir():
            if vm_dir.is_dir() and vm_dir.name.startswith("vm-"):
                vm_name = vm_dir.name[3:]  # Remove "vm-" prefix
                
                state_file = vm_dir / "terraform.tfstate"
                if state_file.exists():
                    terraform_vms.append({
                        "vm_name": vm_name,
                        "state_dir": str(vm_dir),
                        "has_state": True,
                        "state_file": str(state_file)
                    })
        
        return terraform_vms


# Initialize Terraform manager
terraform_manager = TerraformManager()


def register_terraform_tools(server):
    """Register Terraform tools with the MCP server."""
    
    @server.tool()
    async def terraform_create_vm(
        vm_name: str,
        target_node: str,
        cpu_cores: int = 2,
        memory_gb: int = 2,
        disk_size_gb: int = 20,
        template_id: int = 9000,
        ssh_keys: Optional[str] = None,
        vm_tags: Optional[str] = None,
        start_vm: bool = True
    ) -> List[TextContent]:
        """Create a VM using Terraform infrastructure-as-code.
        
        Args:
            vm_name: Name for the new VM
            target_node: Proxmox node to deploy on
            cpu_cores: Number of CPU cores (default: 2)
            memory_gb: Memory in GB (default: 2)
            disk_size_gb: Disk size in GB (default: 20)
            template_id: Template VM ID to clone from (default: 9000)
            ssh_keys: Comma-separated list of SSH public keys
            vm_tags: Comma-separated list of tags
            start_vm: Start the VM after creation (default: true)
        """
        
        # Parse optional parameters
        ssh_keys_list = ssh_keys.split(',') if ssh_keys else []
        vm_tags_list = vm_tags.split(',') if vm_tags else ["mcp-managed", "homelab"]
        
        result = await terraform_manager.create_vm_with_terraform(
            vm_name=vm_name,
            target_node=target_node,
            cpu_cores=cpu_cores,
            memory_gb=memory_gb,
            disk_size_gb=disk_size_gb,
            template_id=template_id,
            ssh_keys=ssh_keys_list,
            vm_tags=vm_tags_list,
            start_vm=start_vm
        )
        
        if result["success"]:
            return [TextContent(
                type="text",
                text=f"""✅ VM created successfully using Terraform!

**VM Details:**
- Name: {result['vm_name']}
- VM ID: {result.get('vm_id', 'Unknown')}
- Node: {result.get('node_name', 'Unknown')}
- Terraform State: {result['terraform_state_dir']}

**Infrastructure-as-Code:**
- Provisioner: Terraform
- State Management: Enabled
- Configuration Stored: Yes

**Next Steps:**
- Use Ansible tools for service deployment
- VM is ready for configuration management
"""
            )]
        else:
            return [TextContent(
                type="text",
                text=f"""❌ VM creation failed using Terraform

**Error:** {result.get('error', 'Unknown error')}

**VM Name:** {result['vm_name']}
**State Directory:** {result.get('terraform_state_dir', 'Unknown')}

**Troubleshooting:**
- Check Proxmox credentials and connectivity
- Verify template {template_id} exists
- Ensure target node has sufficient resources
"""
            )]
    
    @server.tool()
    async def terraform_destroy_vm(vm_name: str) -> List[TextContent]:
        """Destroy a VM created with Terraform.
        
        Args:
            vm_name: Name of the VM to destroy
        """
        
        result = await terraform_manager.destroy_vm_with_terraform(vm_name)
        
        if result["success"]:
            return [TextContent(
                type="text",
                text=f"""✅ VM destroyed successfully using Terraform!

**VM Details:**
- Name: {result['vm_name']}
- Infrastructure-as-Code: Terraform state cleaned up
- Resources: Fully removed from Proxmox

**Terraform Output:**
{result.get('destroy_output', 'No output available')}
"""
            )]
        else:
            return [TextContent(
                type="text",
                text=f"""❌ VM destruction failed

**Error:** {result.get('error', 'Unknown error')}
**VM Name:** {result['vm_name']}

**Troubleshooting:**
- Check if VM exists in Proxmox
- Verify Terraform state is not corrupted
- Manual cleanup may be required
"""
            )]
    
    @server.tool()
    async def terraform_list_managed_vms() -> List[TextContent]:
        """List all VMs managed by Terraform."""
        
        vms = await terraform_manager.list_terraform_managed_vms()
        
        if not vms:
            return [TextContent(
                type="text",
                text="No VMs currently managed by Terraform."
            )]
        
        vm_list = "\n".join([
            f"- {vm['vm_name']} (State: {vm['state_dir']})"
            for vm in vms
        ])
        
        return [TextContent(
            type="text",
            text=f"""🏗️ Terraform-Managed VMs

**Total VMs:** {len(vms)}

{vm_list}

**Infrastructure-as-Code:**
- All VMs have Terraform state files
- Can be destroyed with terraform_destroy_vm
- Configuration stored in terraform/state/
"""
        )]