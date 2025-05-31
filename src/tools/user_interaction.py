"""
MCP tools for user interaction and data collection.
This would allow AI to guide users through configuration.
"""

from typing import Dict, Any, List, Optional
from mcp.server import Tool
from mcp.types import TextContent
import logging

logger = logging.getLogger(__name__)


class UserInteractionTools:
    """Tools that allow AI to interact with users for data collection."""
    
    def __init__(self):
        self.pending_prompts = {}
        self.collected_data = {}
    
    def get_tools(self) -> List[Tool]:
        """Get user interaction tools."""
        return [
            Tool(
                name="request_user_input",
                description="Request specific information from the user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Question to ask the user"
                        },
                        "input_type": {
                            "type": "string",
                            "enum": ["text", "password", "choice", "confirm"],
                            "description": "Type of input expected"
                        },
                        "choices": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Valid choices (for choice type)"
                        },
                        "default": {
                            "type": "string",
                            "description": "Default value if user presses enter"
                        }
                    },
                    "required": ["prompt", "input_type"]
                }
            ),
            Tool(
                name="start_guided_setup",
                description="Start a guided setup process for a specific service",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "setup_type": {
                            "type": "string",
                            "enum": ["proxmox", "vm_creation", "ansible_playbook"],
                            "description": "Type of setup to guide user through"
                        }
                    },
                    "required": ["setup_type"]
                }
            )
        ]
    
    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle tool execution."""
        if name == "request_user_input":
            return self._request_input(arguments)
        elif name == "start_guided_setup":
            return self._start_guided_setup(arguments)
        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
    
    def _request_input(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Request input from user (this would need client support)."""
        # This is a conceptual implementation
        # In reality, this would need to communicate with the client
        # to actually prompt the user
        
        prompt = arguments.get("prompt")
        input_type = arguments.get("input_type")
        
        # This would trigger a prompt in the client
        # For now, we return instructions
        return [TextContent(
            type="text",
            text=f"[USER_INPUT_REQUIRED]\nType: {input_type}\nPrompt: {prompt}\n\n" +
                 "Note: Direct user input collection via AI is not yet implemented. " +
                 "Please use the wizard commands like 'setup proxmox' instead."
        )]
    
    def _start_guided_setup(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Guide user to start a setup wizard."""
        setup_type = arguments.get("setup_type")
        
        commands = {
            "proxmox": "setup proxmox",
            "vm_creation": "create vm",
            "ansible_playbook": "run playbook"
        }
        
        command = commands.get(setup_type, "")
        
        return [TextContent(
            type="text",
            text=f"To start the {setup_type} setup wizard, type: '{command}'\n\n" +
                 f"This will guide you through the configuration process step by step."
        )]


# Example of how AI could use these tools:
"""
User: I want to set up my Proxmox server
AI: I'll help you configure Proxmox. Let me start the setup wizard for you.

[AI calls start_guided_setup with setup_type="proxmox"]

AI: Type 'setup proxmox' to begin the configuration wizard. This will guide you through:
- Entering your Proxmox server IP
- Providing credentials
- Testing the connection
- Creating an API token for better reliability
"""