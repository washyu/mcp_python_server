"""
Simple Ansible runner for executing playbooks and ad-hoc commands.
"""

import asyncio
import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class AnsibleRunner:
    """Simplified Ansible runner for MCP integration."""
    
    def __init__(self):
        self.ansible_path = "ansible-playbook"
        self.ansible_command = "ansible"
        
    async def run_playbook_dict(
        self,
        playbook: Dict[str, Any],
        inventory: Dict[str, Any],
        extra_vars: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run an Ansible playbook from a dictionary definition.
        
        Args:
        
            playbook: Playbook definition as a dictionary
            inventory: Inventory as a dictionary
            extra_vars: Extra variables to pass to playbook
            
        Returns:
            Result dictionary with success status and output
        """
        try:
            # Create temporary files for playbook and inventory
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as playbook_file:
                import yaml
                yaml.dump([playbook], playbook_file)
                playbook_path = playbook_file.name
                
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as inventory_file:
                yaml.dump({"all": {"hosts": inventory}}, inventory_file)
                inventory_path = inventory_file.name
                
            # Build ansible-playbook command
            cmd = [
                self.ansible_path,
                "-i", inventory_path,
                playbook_path
            ]
            
            if extra_vars:
                cmd.extend(["-e", json.dumps(extra_vars)])
                
            # Run the playbook
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            # Clean up temp files
            Path(playbook_path).unlink(missing_ok=True)
            Path(inventory_path).unlink(missing_ok=True)
            
            return {
                "success": proc.returncode == 0,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
                "returncode": proc.returncode
            }
            
        except Exception as e:
            logger.error(f"Failed to run playbook: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def run_ad_hoc_command(
        self,
        hosts: str,
        module: str,
        args: Optional[str] = None,
        inventory: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run an ad-hoc Ansible command.
        
        Args:
            hosts: Host pattern (e.g., "all", "webservers")
            module: Ansible module to use (e.g., "ping", "shell")
            args: Module arguments
            inventory: Inventory dictionary (optional)
            
        Returns:
            Result dictionary
        """
        try:
            cmd = [self.ansible_command, hosts, "-m", module]
            
            if args:
                cmd.extend(["-a", args])
                
            if inventory:
                # Create temp inventory file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as inv_file:
                    import yaml
                    yaml.dump({"all": {"hosts": inventory}}, inv_file)
                    inv_path = inv_file.name
                    cmd.extend(["-i", inv_path])
                    
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            # Clean up
            if inventory:
                Path(inv_path).unlink(missing_ok=True)
                
            return {
                "success": proc.returncode == 0,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
                "returncode": proc.returncode
            }
            
        except Exception as e:
            logger.error(f"Failed to run ad-hoc command: {e}")
            return {
                "success": False,
                "error": str(e)
            }