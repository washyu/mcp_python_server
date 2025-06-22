"""
Universal Homelab MCP Server - Infrastructure Automation Toolkit for AI Agents

This MCP server provides tools that enable ANY AI agent to automatically:
- Discover and assess hardware capabilities
- Install and configure virtualization platforms (Proxmox, LXD, Docker)
- Deploy services with smart defaults and best practices
- Troubleshoot and optimize homelab infrastructure
- Make informed technology choices with comparative analysis

Primary Purpose: Let AI agents build complete homelab environments autonomously
with minimal human intervention, while educating users about the decisions made.
"""

import asyncio
import logging
import re
from typing import Any, Dict, List
from mcp.server import FastMCP
from mcp.types import TextContent
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import StreamingResponse, JSONResponse
from starlette.middleware.cors import CORSMiddleware
import json
import ollama
from src.tools.proxmox_discovery import PROXMOX_TOOLS, handle_proxmox_tool
from src.tools.vm_creation import (
    create_vm_tool,
    start_vm_tool,
    stop_vm_tool,
    delete_vm_tool,
    get_vm_status_tool
)
from src.tools.homelab_tools import HOMELAB_TOOLS, handle_homelab_tool
from src.tools.lxd_tools import LXD_TOOLS, handle_lxd_tool
from src.tools.agent_homelab_tools import AGENT_HOMELAB_TOOLS, handle_agent_homelab_tool
from src.tools.homelab_context_tools import HOMELAB_CONTEXT_TOOLS, handle_homelab_context_tool
from src.tools.ansible_tools import ANSIBLE_TOOLS, handle_ansible_tool
from src.tools.auth_setup_tools import AUTH_SETUP_TOOLS, handle_auth_setup_tool
from src.tools.terraform_tools import register_terraform_tools
from src.tools.system_hardware_discovery import SYSTEM_HARDWARE_TOOLS, handle_system_hardware_tool
from src.tools.remote_hardware_discovery import REMOTE_HARDWARE_TOOLS, register_remote_hardware_tools
from src.tools.hardware_discovery_guide import HARDWARE_GUIDE_TOOLS

logger = logging.getLogger(__name__)


class HomelabMCPServer:
    """
    Universal Homelab MCP Server - Infrastructure Automation Toolkit
    
    Enables ANY AI agent to automatically provision, configure, and manage
    complete homelab environments with minimal human intervention.
    
    Core Capabilities:
    - Autonomous infrastructure setup (Proxmox, LXD, Docker)
    - Smart technology selection with comparative analysis
    - Service deployment with industry best practices
    - Educational explanations of all decisions made
    """
    
    def __init__(self, name: str = "universal-homelab-mcp", host: str = "127.0.0.1", port: int = 8000):
        """Initialize the MCP server."""
        self.name = name
        self.host = host
        self.port = port
        # Use stateless HTTP mode to bypass FastMCP session ID bug
        self.mcp = FastMCP(name, host=host, port=port, stateless_http=True)
        self._register_tools()
        self._setup_chat_app()
    
    def _register_tools(self):
        """Register all MCP tools for AI-driven homelab automation."""
        logger.info("Registering Universal Homelab MCP tools...")
        
        # PRIORITY 0: Authentication setup tools (foundational)
        for tool in AUTH_SETUP_TOOLS:
            logger.info(f"Registering Auth tool: {tool.name}")
            
            def make_auth_handler(tool_name: str):
                async def handler(**kwargs) -> List[TextContent]:
                    return await handle_auth_setup_tool(tool_name, kwargs)
                return handler
            
            self.mcp.tool(tool.name, tool.description)(
                make_auth_handler(tool.name)
            )
        
        # PRIORITY 1: Agent-driven automation tools (main feature)
        for tool in AGENT_HOMELAB_TOOLS:
            logger.info(f"Registering Agent tool: {tool.name}")
            
            def make_agent_handler(tool_name: str):
                async def handler(**kwargs) -> List[TextContent]:
                    return await handle_agent_homelab_tool(tool_name, kwargs)
                return handler
            
            self.mcp.tool(tool.name, tool.description)(
                make_agent_handler(tool.name)
            )
        
        # PRIORITY 2: Homelab Context and Topology Management
        for tool in HOMELAB_CONTEXT_TOOLS:
            logger.info(f"Registering Context tool: {tool.name}")
            
            def make_context_handler(tool_name: str):
                async def handler(**kwargs) -> List[TextContent]:
                    return await handle_homelab_context_tool(tool_name, kwargs)
                return handler
            
            self.mcp.tool(tool.name, tool.description)(
                make_context_handler(tool.name)
            )
        
        # PRIORITY 3: Infrastructure discovery and management tools
        for tool in PROXMOX_TOOLS:
            logger.info(f"Registering Infrastructure tool: {tool.name}")
            
            def make_proxmox_handler(tool_name: str):
                async def handler(**kwargs) -> List[TextContent]:
                    return await handle_proxmox_tool(tool_name, kwargs)
                return handler
            
            self.mcp.tool(tool.name, tool.description)(
                make_proxmox_handler(tool.name)
            )
        
        # PRIORITY 4: Container platform tools  
        for tool in LXD_TOOLS:
            logger.info(f"Registering Container tool: {tool.name}")
            
            def make_lxd_handler(tool_name: str):
                async def handler(**kwargs) -> List[TextContent]:
                    return await handle_lxd_tool(tool_name, kwargs)
                return handler
            
            self.mcp.tool(tool.name, tool.description)(
                make_lxd_handler(tool.name)
            )
        
        # PRIORITY 5: Ansible automation tools (generic service deployment)
        for tool in ANSIBLE_TOOLS:
            logger.info(f"Registering Ansible tool: {tool.name}")
            
            def make_ansible_handler(tool_name: str):
                async def handler(**kwargs) -> List[TextContent]:
                    return await handle_ansible_tool(tool_name, kwargs)
                return handler
            
            self.mcp.tool(tool.name, tool.description)(
                make_ansible_handler(tool.name)
            )
        
        # PRIORITY 5.5: Terraform infrastructure-as-code tools
        register_terraform_tools(self.mcp)
        logger.info("Registered Terraform infrastructure-as-code tools")
        
        # PRIORITY 5.6: Local system hardware discovery tools
        for tool in SYSTEM_HARDWARE_TOOLS:
            logger.info(f"Registering System Hardware tool: {tool.name}")
            
            def make_hardware_handler(tool_name: str):
                async def handler(**kwargs) -> List[TextContent]:
                    return await handle_system_hardware_tool(tool_name, kwargs)
                return handler
            
            self.mcp.tool(tool.name, tool.description)(
                make_hardware_handler(tool.name)
            )
        
        # PRIORITY 5.7: Remote hardware discovery and context building
        register_remote_hardware_tools(self.mcp)
        logger.info("Registered Remote Hardware Discovery tools")
        
        # PRIORITY 5.8: Hardware discovery guide tools
        from src.tools.hardware_discovery_guide import register_hardware_guide_tools
        register_hardware_guide_tools(self.mcp)
        logger.info("Registered Hardware Discovery Guide tools")
        
        # PRIORITY 6: User guidance tools (when agent needs human input)
        for tool in HOMELAB_TOOLS:
            logger.info(f"Registering Guidance tool: {tool.name}")
            
            def make_homelab_handler(tool_name: str):
                async def handler(**kwargs) -> List[TextContent]:
                    return await handle_homelab_tool(tool_name, kwargs)
                return handler
            
            self.mcp.tool(tool.name, tool.description)(
                make_homelab_handler(tool.name)
            )
        
        # Register VM creation tool
        self.mcp.tool(
            name="create_vm",
            description="Create a new VM from cloud-init template with automatic resource placement"
        )(self._create_vm_handler)
        
        # Register VM lifecycle management tools
        self.mcp.tool(
            name="start_vm",
            description="Start a stopped VM"
        )(self._start_vm_handler)
        
        self.mcp.tool(
            name="stop_vm",
            description="Stop a running VM gracefully or forcefully"
        )(self._stop_vm_handler)
        
        self.mcp.tool(
            name="delete_vm",
            description="Delete a VM permanently"
        )(self._delete_vm_handler)
        
        self.mcp.tool(
            name="get_vm_status",
            description="Get current status and details of a VM"
        )(self._get_vm_status_handler)
        
        total_tools = (len(AGENT_HOMELAB_TOOLS) + len(HOMELAB_CONTEXT_TOOLS) + len(PROXMOX_TOOLS) + 
                      len(LXD_TOOLS) + len(HOMELAB_TOOLS) + len(AUTH_SETUP_TOOLS) + len(ANSIBLE_TOOLS) +
                      len(SYSTEM_HARDWARE_TOOLS) + len(REMOTE_HARDWARE_TOOLS) + len(HARDWARE_GUIDE_TOOLS) + 5)
        logger.info(f"Successfully registered {total_tools} MCP tools for AI-driven homelab automation")
        logger.info(f"  🤖 Agent Automation: {len(AGENT_HOMELAB_TOOLS)} tools (PRIMARY FEATURE)")
        logger.info(f"  🏠 Homelab Context: {len(HOMELAB_CONTEXT_TOOLS)} tools")
        logger.info(f"  🏗️  Infrastructure: {len(PROXMOX_TOOLS)} tools") 
        logger.info(f"  📦 Containers: {len(LXD_TOOLS)} tools")
        logger.info(f"  👥 User Guidance: {len(HOMELAB_TOOLS)} tools")
        logger.info(f"  🖥️  VM Management: 5 tools")
    
    def _setup_chat_app(self):
        """Set up the chat application with MCP tool orchestration."""
        # Create routes for the chat API
        routes = [
            Route("/api/chat", self._chat_endpoint, methods=["POST"]),
            Route("/api/tools", self._tools_endpoint, methods=["GET"]),
            Route("/health", self._health_endpoint, methods=["GET"]),
        ]
        
        # Create Starlette app for chat endpoints
        self.chat_app = Starlette(routes=routes)
        
        # Add CORS middleware
        self.chat_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    async def _tools_endpoint(self, request):
        """Return available MCP tools."""
        try:
            # Get all registered tools
            tools = []
            
            # Add each tool category with proper JSON serialization
            for tool_set in [PROXMOX_TOOLS, LXD_TOOLS, HOMELAB_TOOLS, AGENT_HOMELAB_TOOLS, 
                           HOMELAB_CONTEXT_TOOLS, ANSIBLE_TOOLS, AUTH_SETUP_TOOLS, SYSTEM_HARDWARE_TOOLS,
                           REMOTE_HARDWARE_TOOLS]:
                for tool in tool_set:
                    tools.append({
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                    })
            
            # Add hardware guide tools
            for tool in HARDWARE_GUIDE_TOOLS:
                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                })
            
            # Add VM management tools
            vm_tools = [
                {"name": "create_vm", "description": "Create a new VM from cloud-init template"},
                {"name": "start_vm", "description": "Start a stopped VM"},
                {"name": "stop_vm", "description": "Stop a running VM"},
                {"name": "delete_vm", "description": "Delete a VM permanently"},
                {"name": "get_vm_status", "description": "Get current status of a VM"}
            ]
            tools.extend(vm_tools)
            
            return JSONResponse({"tools": tools, "count": len(tools)})
        except Exception as e:
            logger.error(f"Error getting tools: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)
    
    async def _health_endpoint(self, request):
        """Health check endpoint."""
        return JSONResponse({"status": "healthy", "service": "mcp-chat-server"})
    
    async def _chat_endpoint(self, request):
        """Handle chat requests with MCP tool orchestration."""
        try:
            data = await request.json()
            messages = data.get('messages', [])
            model = data.get('model', 'llama3.1:8b')
            stream = data.get('stream', True)
            
            if stream:
                return StreamingResponse(
                    self._stream_chat_with_tools(messages, model),
                    media_type="text/plain"
                )
            else:
                response = await self._chat_with_tools(messages, model)
                return JSONResponse(response)
                
        except Exception as e:
            logger.error(f"Chat endpoint error: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)
    
    async def _stream_chat_with_tools(self, messages: List[Dict], model: str):
        """Stream chat responses with AI-driven tool execution and wizard workflows."""
        try:
            # Enhanced system message for wizard-driven automation
            system_msg = """You are a homelab automation wizard with access to 75+ infrastructure management tools. Your role is to guide users through complete homelab setup workflows by asking clarifying questions and executing tools.

**CRITICAL: How to Execute Tools**
When you need to call a tool, use this TEMPLATE format - just replace the placeholders:

For hardware discovery:
```
EXECUTE_TOOL: discover_remote_system IP: 192.168.50.41
```

For VM creation:
```
EXECUTE_TOOL: create_vm NAME: my-server CORES: 4 MEMORY: 8
```

IMPORTANT: 
- Just replace the placeholder values (IP, NAME, CORES, etc.)
- No JSON syntax needed - much simpler!
- Templates prevent malformed syntax

**Your Approach:**
1. **Ask questions first** to understand user goals (media server, development, AI, etc.)
2. **Discover current infrastructure** using discovery tools WITH PROPER SYNTAX
3. **Plan network accessibility** - CRITICAL for homelab services
4. **Propose specific solutions** with step-by-step execution
5. **Execute tools using the EXECUTE_TOOL format** - DO NOT pretend or hallucinate results
6. **Guide users through wizards** for complex setups (Proxmox, TrueNAS, WordPress, etc.)

**🌐 CRITICAL: Network Accessibility Planning**
When setting up ANY service (Plex, web servers, databases, etc.), you MUST ask about network access:

1. **Default Assumption**: Services should be accessible to ALL homelab devices
   - Xbox, phones, tablets, laptops should access Plex
   - Web services should be reachable from any device on the network
   - Development servers should be accessible for testing

2. **Network Planning Questions**:
   - "Is this for your entire homelab network, or specific subnets?"
   - "Do you have VLANs or network segmentation I should know about?"
   - "Should this be accessible from outside your home network (via VPN/reverse proxy)?"

3. **Configuration Requirements**:
   - **Bind to 0.0.0.0** (all interfaces) not just localhost
   - **Open required ports** in firewall if needed
   - **Configure proper subnet access** for services
   - **Set up reverse proxy** if external access needed

**Example Network Planning:**
User: "Set up a Plex server"
You: "Great! I'll set up Plex so all your devices can access it. A few questions:
- Should your Xbox, phones, and tablets all be able to stream from this?
- Do you have any network VLANs or subnets I should configure access for?
- Would you like external access via VPN or reverse proxy for remote streaming?"

Then configure Plex with:
- Bind to 0.0.0.0:32400 (accessible from all network devices)
- Firewall rules for port 32400
- Proper network interface configuration

**Available Tool Categories:**
- Infrastructure Discovery: proxmox_list_nodes, proxmox_discover_hardware, discover-homelab-topology
- Hardware Discovery: discover_remote_system (remote hardware specs), discover_local_hardware (MCP server hardware), hardware_discovery_guide (tool selection help)
- VM Management: create_vm, start_vm, stop_vm, delete_vm
- Container Operations: LXD tools for container management
- Authentication: SSH key deployment and user setup, setup_remote_ssh_access
- Service Deployment: WordPress, Docker, databases, media servers
- Automation: Ansible playbooks for service installation

**CRITICAL: Hardware Discovery Tool Selection**
- **For server hardware specs**: ALWAYS use `EXECUTE_TOOL: discover_remote_system IP: X.X.X.X`
- **For network scanning only**: Use `discover-homelab-topology` 
- **For MCP server hardware**: Use `discover_local_hardware`
- **For tool guidance**: Use `hardware_discovery_guide`

**ABSOLUTELY FORBIDDEN - NEVER DO THIS**:
- NEVER provide hardware specs unless the tool returns them
- NEVER guess CPU models (no Intel i7, AMD Ryzen, etc.)
- NEVER make up RAM amounts (no 4GB, 8GB, 64GB guesses)
- NEVER invent storage details (no SSD/HDD specs without tool data)
- If discover_remote_system fails, say "SSH access failed" - DO NOT make up specs
- For Raspberry Pi systems, NEVER assume model - could be Pi 4, Pi 5, etc.

**More Template Examples:**
```
EXECUTE_TOOL: create_vm NAME: web-server CORES: 4 MEMORY: 8 DISK: 100
EXECUTE_TOOL: start_vm ID: 203
EXECUTE_TOOL: proxmox_list_nodes
```

**CRITICAL: Tool Execution Rules**
1. NEVER hallucinate or make up tool outputs - if a tool fails, say "Tool failed" and explain why
2. ALWAYS use the EXECUTE_TOOL format when calling tools
3. IMMEDIATELY after writing EXECUTE_TOOL, say "Waiting for tool result..." and STOP generating
4. If a tool fails due to SSH access, say "Cannot access system via SSH" and offer setup_remote_ssh_access
5. If hardware discovery fails, say "Unable to determine hardware specs" - DO NOT guess or make up specifications
6. NEVER provide hardware specs unless the tool succeeds and returns real data
7. When you write EXECUTE_TOOL, the system will execute it and provide results - DO NOT continue until you see the result

**Wizard Behaviors:**
- Start by asking "What would you like to set up in your homelab?"
- Use discovery tools to understand current infrastructure
- Propose concrete next steps with tool execution
- Execute tools automatically after user approval
- Provide real-time status updates during tool execution

**Example Workflow:**
User: "I want to set up a media server"
You: "Great! Let me first discover your current infrastructure and then guide you through setting up Plex or Jellyfin. Let me check your Proxmox nodes first..."
[Execute: proxmox_list_nodes]
[Execute: proxmox_discover_hardware]
"I see you have [X] available. Would you like me to create a VM for Plex with [recommended specs]?"
[If yes, execute: create_vm with media server template]

Always drive the conversation forward with concrete actions."""

            # Prepare messages for Ollama
            ollama_messages = [{"role": "system", "content": system_msg}]
            ollama_messages.extend(messages)
            
            # Start chat with Ollama with parameters to prevent cutoff
            response = ollama.chat(
                model=model,
                messages=ollama_messages,
                stream=True,
                options={
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "stop": [],  # Don't stop on any specific tokens
                    "num_predict": 4096,  # Much longer responses to prevent cutoffs
                    "repeat_penalty": 1.1,  # Reduce repetition
                }
            )
            
            full_response = ""
            buffer = ""
            tool_execution_detected = False
            
            for chunk in response:
                content = chunk['message']['content']
                full_response += content
                buffer += content
                
                # Check for tool execution pattern in buffer
                if not tool_execution_detected and "EXECUTE_TOOL:" in buffer:
                    # Check if we have a complete tool command (look for newline or enough content)
                    if '\n' in buffer[buffer.index("EXECUTE_TOOL:"):] or len(buffer[buffer.index("EXECUTE_TOOL:"):]) > 50:
                        tool_pattern = r'EXECUTE_TOOL:\s*(\w+)\s+(.+?)(?:\n|$)'
                        tool_match = re.search(tool_pattern, buffer)
                        
                        if tool_match:
                            tool_execution_detected = True
                            # Stop streaming AI response - we need to execute the tool
                            yield f"data: {json.dumps({'content': content, 'type': 'text'})}\n\n"
                            break
                
                # Stream content if no tool execution detected yet
                if not tool_execution_detected:
                    yield f"data: {json.dumps({'content': content, 'type': 'text'})}\n\n"
            
            # Process tool execution if detected (either during streaming or after)
            if tool_execution_detected or "EXECUTE_TOOL:" in full_response:
                
                # Try template format first, then fallback to JSON format
                patterns = [
                    r'EXECUTE_TOOL:\s*(\w+)\s+(.+?)(?:\n|$)',  # Template format: EXECUTE_TOOL: tool_name KEY: value KEY: value
                    r'EXECUTE_TOOL:\s*(\w+)\s+ARGUMENTS:\s*(\{[^}]*\})',  # Complete JSON (backward compatibility)
                    r'EXECUTE_TOOL:\s*(\w+).*?ARGUMENTS:\s*(\{[^}]*\})',  # Multi-line JSON
                    r'EXECUTE_TOOL:\s*(\w+)\s*ARGUMENTS:\s*(\{[^}]*\})',  # No newline JSON
                    r'EXECUTE_TOOL:\s*(\w+).*?ARGUMENTS:\s*(\{.*?\})',    # Greedy JSON
                    r'EXECUTE_TOOL:\s*(\w+).*?ARGUMENTS:\s*(\{[^}]*)',    # Incomplete JSON
                ]
                
                tool_match = None
                matched_pattern = None
                for i, pattern in enumerate(patterns):
                    tool_match = re.search(pattern, full_response, re.DOTALL)
                    if tool_match:
                        matched_pattern = i
                        break
                
                if tool_match:
                    tool_name = tool_match.group(1)
                    raw_args = tool_match.group(2)
                    
                    # Parse based on pattern type
                    if matched_pattern == 0:  # Template format
                        tool_args = self._parse_template_args(tool_name, raw_args)
                    else:  # JSON format
                        # Try to fix incomplete JSON for later patterns
                        if matched_pattern is not None and matched_pattern >= 5 and tool_name == "discover_remote_system" and '"ip_address"' in raw_args:
                            # Extract just the IP address if it's there
                            ip_match = re.search(r'"ip_address":\s*"([^"]*)"', raw_args)
                            if ip_match:
                                ip_address = ip_match.group(1)
                                raw_args = f'{{"ip_address": "{ip_address}"}}'
                        
                        try:
                            tool_args = json.loads(raw_args)
                        except json.JSONDecodeError as e:
                            yield f"data: {json.dumps({'content': f'\\n❌ Invalid JSON: {str(e)}\\n', 'type': 'error'})}\n\n"
                            tool_args = None
                    
                    # Only execute if we have valid tool_args
                    if tool_args is not None:
                        try:
                            # Execute the tool
                            yield f"data: {json.dumps({'content': f'\\n\\n🔧 Executing tool: {tool_name}...\\n', 'type': 'tool_start'})}\n\n"
                            
                            result = await self._execute_mcp_tool(tool_name, tool_args)
                            
                            yield f"data: {json.dumps({'content': f'\\n📊 Tool Result:\\n{result}\\n\\n', 'type': 'tool_result'})}\n\n"
                            
                            # Add tool result to conversation for AI to see
                            messages.append({"role": "assistant", "content": f"EXECUTE_TOOL: {tool_name}\\nARGUMENTS: {json.dumps(tool_args)}"})
                            
                            # Add stronger instruction if tool failed
                            if "failed" in result.lower() or "error" in result.lower():
                                messages.append({"role": "system", "content": f"Tool Result: {result}\\n\\nCRITICAL: The tool FAILED. You MUST NOT provide any hardware specifications. Instead, say exactly: 'Unable to determine hardware specs - SSH access failed. Would you like me to help set up SSH access?' DO NOT mention any CPU models, RAM amounts, or storage details."})
                            
                            # Continue conversation with tool result
                            continuation_messages = [{"role": "system", "content": system_msg}]
                            continuation_messages.extend(messages)
                            
                            # Get AI's response to the tool result
                            continuation = ollama.chat(
                                model=model,
                                messages=continuation_messages,
                                stream=True,
                                options={
                                    "temperature": 0.7,
                                    "top_p": 0.9,
                                    "stop": [],
                                    "num_predict": 4096,
                                    "repeat_penalty": 1.1,
                                }
                            )
                            
                            for cont_chunk in continuation:
                                cont_content = cont_chunk['message']['content']
                                yield f"data: {json.dumps({'content': cont_content, 'type': 'text'})}\n\n"
                            
                        except Exception as e:
                            yield f"data: {json.dumps({'content': f'\\n❌ Tool execution error: {str(e)}\\n', 'type': 'error'})}\n\n"
                # If no match found, tool execution fails silently (AI will continue normally)
            
            # Still analyze for other patterns (backwards compatibility)
            async for tool_chunk in self._analyze_and_execute_tools(full_response, messages):
                yield tool_chunk
            
            # Always send done indicator when streaming completes
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            logger.error(f"Streaming chat error: {e}")
            yield f"data: {json.dumps({'content': f'Error: {str(e)}', 'type': 'error'})}\n\n"
    
    async def _analyze_and_execute_tools(self, ai_response: str, conversation_history: List[Dict]):
        """Analyze AI response and execute tools automatically when appropriate."""
        try:
            # Parse AI intent for automatic tool execution
            response_lower = ai_response.lower()
            
            # Discovery triggers
            if any(phrase in response_lower for phrase in 
                   ['let me check', 'let me discover', 'let me see your', 'first check']):
                
                if 'proxmox' in response_lower or 'infrastructure' in response_lower:
                    yield f"data: {json.dumps({'content': '\\n\\n🔍 **Discovering Proxmox infrastructure...**\\n', 'type': 'tool_start'})}\n\n"
                    
                    # Execute proxmox discovery
                    result = await self._execute_mcp_tool('proxmox_list_nodes', {})
                    if result:
                        yield f"data: {json.dumps({'content': f'✅ **Discovery complete:**\\n{result}\\n', 'type': 'tool_result'})}\n\n"
            
            # Hardware discovery triggers - extract IP addresses and use correct tool
            import re
            ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
            ips_found = re.findall(ip_pattern, ai_response)
            
            if any(phrase in response_lower for phrase in 
                   ['hardware', 'system specs', 'check the hardware', 'scan the device', 'discover hardware']):
                
                if ips_found:
                    ip_address = ips_found[0]  # Use first IP found
                    yield f"data: {json.dumps({'content': f'\\n\\n🔍 **Scanning hardware at {ip_address}...**\\n', 'type': 'tool_start'})}\n\n"
                    
                    # Execute remote hardware discovery
                    result = await self._execute_mcp_tool('discover_remote_system', {'ip_address': ip_address})
                    if result:
                        yield f"data: {json.dumps({'content': f'✅ **Hardware scan complete:**\\n{result}\\n', 'type': 'tool_result'})}\n\n"
            
            # VM creation triggers
            if any(phrase in response_lower for phrase in 
                   ['create a vm', 'create vm', 'new virtual machine']):
                
                # Extract VM details from conversation
                vm_suggestions = self._extract_vm_requirements(ai_response, conversation_history)
                if vm_suggestions:
                    yield f"data: {json.dumps({'content': f'\\n\\n🚀 **Ready to create VM with these specs:**\\n{vm_suggestions}\\n*Say \"yes\" to proceed or provide different requirements*\\n', 'type': 'tool_proposal'})}\n\n"
            
            # Service setup triggers
            if any(service in response_lower for service in 
                   ['plex', 'jellyfin', 'wordpress', 'docker', 'nextcloud']):
                
                service_type = self._identify_service_type(response_lower)
                network_guidance = self._get_network_guidance(service_type)
                
                yield f"data: {json.dumps({'content': f'\\n\\n⚙️ **{service_type} Setup Wizard:**\\n{network_guidance}\\n\\nI can set this up automatically. Would you like me to:\\n1. Create a VM for {service_type}\\n2. Install and configure {service_type} (accessible to all network devices)\\n3. Set up networking and firewall rules\\n4. Configure external access if needed\\n\\nSay \"start setup\" to begin!\\n', 'type': 'wizard_offer'})}\n\n"
            
        except Exception as e:
            logger.error(f"Tool analysis error: {e}")
            yield f"data: {json.dumps({'content': f'\\nTool execution error: {str(e)}', 'type': 'error'})}\n\n"
    
    async def _execute_mcp_tool(self, tool_name: str, args: Dict) -> str:
        """Execute an MCP tool and return the result."""
        try:
            # Route to appropriate tool handler
            if tool_name.startswith('proxmox_'):
                result = await handle_proxmox_tool(tool_name, args)
            elif tool_name in ['create_vm', 'start_vm', 'stop_vm', 'delete_vm', 'get_vm_status']:
                result = await self._handle_vm_tool(tool_name, args)
            elif tool_name == 'discover_remote_system':
                from src.tools.remote_hardware_discovery import remote_discovery
                discovery_result = await remote_discovery.discover_remote_hardware(**args)
                # Format the result for display
                if discovery_result.get('hardware'):
                    hw = discovery_result['hardware']
                    text = f"🔍 **Remote System Discovery: {args.get('ip_address')}**\n\n"
                    text += f"**System Information:**\n"
                    text += f"- Hostname: {hw.hostname}\n"
                    text += f"- OS: {hw.distribution}\n"
                    text += f"- Kernel: {hw.kernel}\n"
                    if hw.cpu:
                        text += f"\n**CPU:**\n"
                        text += f"- Model: {hw.cpu.model}\n"
                        text += f"- Cores: {hw.cpu.cores}, Threads: {hw.cpu.threads}\n"
                    if hw.memory:
                        text += f"\n**Memory:**\n"
                        text += f"- Total: {hw.memory.total_gb:.1f} GB\n"
                    result = [TextContent(type="text", text=text)]
                else:
                    error_msg = f"❌ Hardware discovery failed: {', '.join(discovery_result.get('errors', ['Unknown error']))}"
                    result = [TextContent(type="text", text=error_msg)]
            else:
                # Handle other tool categories
                result = [TextContent(type="text", text=f"Tool {tool_name} executed with args: {args}")]
            
            # Extract text content from result
            if result and len(result) > 0:
                return result[0].text
            return "Tool executed successfully"
            
        except Exception as e:
            logger.error(f"Tool execution error for {tool_name}: {e}")
            return f"Error executing {tool_name}: {str(e)}"
    
    async def _handle_vm_tool(self, tool_name: str, args: Dict):
        """Handle VM management tools."""
        if tool_name == 'create_vm':
            return await self._create_vm_handler(**args)
        elif tool_name == 'start_vm':
            return await self._start_vm_handler(**args)
        elif tool_name == 'stop_vm':
            return await self._stop_vm_handler(**args)
        elif tool_name == 'delete_vm':
            return await self._delete_vm_handler(**args)
        elif tool_name == 'get_vm_status':
            return await self._get_vm_status_handler(**args)
        else:
            return [TextContent(type="text", text=f"Unknown VM tool: {tool_name}")]
    
    def _extract_vm_requirements(self, ai_response: str, conversation: List[Dict]) -> str:
        """Extract VM requirements from AI response and conversation context."""
        # Simple parsing - could be enhanced with NLP
        specs = []
        
        if 'media server' in ai_response.lower():
            specs.append("Purpose: Media Server (Plex/Jellyfin)")
            specs.append("CPU: 4 cores")
            specs.append("Memory: 8GB")
            specs.append("Storage: 100GB")
            specs.append("Network: Accessible to all homelab devices (Xbox, phones, tablets)")
            specs.append("Ports: Media streaming ports (32400 for Plex, 8096 for Jellyfin)")
        elif 'web server' in ai_response.lower():
            specs.append("Purpose: Web Server")
            specs.append("CPU: 2 cores")
            specs.append("Memory: 4GB")
            specs.append("Storage: 50GB")
            specs.append("Network: Accessible to all network devices")
            specs.append("Ports: HTTP (80), HTTPS (443)")
        elif 'development' in ai_response.lower():
            specs.append("Purpose: Development Environment")
            specs.append("CPU: 4 cores")
            specs.append("Memory: 8GB")
            specs.append("Storage: 100GB")
            specs.append("Network: Accessible for testing from all development devices")
            specs.append("Ports: Custom application ports as needed")
        
        return "\\n".join(specs) if specs else "General purpose VM with default specs\\nNetwork: Accessible to all homelab devices"
    
    def _identify_service_type(self, text: str) -> str:
        """Identify the service type from text."""
        services = {
            'plex': 'Plex Media Server',
            'jellyfin': 'Jellyfin Media Server',
            'wordpress': 'WordPress',
            'docker': 'Docker Container Platform',
            'nextcloud': 'Nextcloud File Sharing'
        }
        
        for service, display_name in services.items():
            if service in text:
                return display_name
        
        return "Service"
    
    def _get_network_guidance(self, service_type: str) -> str:
        """Get network accessibility guidance for specific services."""
        guidance_map = {
            'Plex Media Server': '📺 **Network Access Planning:** This Plex server will be accessible to:\n• Xbox, PlayStation, smart TVs for streaming\n• Phones and tablets for mobile access\n• Laptops and desktops for web interface\n• External access for remote streaming (optional)',
            
            'Jellyfin Media Server': '📺 **Network Access Planning:** This Jellyfin server will be accessible to:\n• All media devices (Xbox, phones, tablets, smart TVs)\n• Web browsers on any network device\n• Mobile apps for remote streaming\n• External access for remote viewing (optional)',
            
            'WordPress': '🌐 **Network Access Planning:** This WordPress site will be accessible to:\n• All devices on your network for testing/editing\n• External visitors if you set up reverse proxy\n• Mobile devices for content management\n• Development team if this is a team project',
            
            'Docker Container Platform': '🐳 **Network Access Planning:** Docker services will be accessible to:\n• All network devices that need to access container apps\n• Other containers within Docker networks\n• External access through reverse proxy if needed\n• Development machines for testing',
            
            'Nextcloud File Sharing': '☁️ **Network Access Planning:** Nextcloud will be accessible to:\n• All family/team devices for file sync\n• Mobile apps for photo backup and file access\n• External access for remote file management\n• Backup systems and sync clients'
        }
        
        return guidance_map.get(service_type, '🌐 **Network Access Planning:** This service will be configured for network-wide access by default.')
    
    def _parse_template_args(self, tool_name: str, template_str: str) -> Dict[str, Any]:
        """Parse template format arguments into a dictionary."""
        args = {}
        
        # Parse KEY: value pairs from template string
        # Example: "IP: 192.168.50.41 USER: root" -> {"ip_address": "192.168.50.41", "ssh_user": "root"}
        
        pairs = re.findall(r'(\w+):\s*([^\s]+(?:\s+[^\s:]+)*?)(?=\s+\w+:|$)', template_str)
        
        for key, value in pairs:
            key = key.upper()
            value = value.strip()
            
            # Map template keys to tool parameter names
            if tool_name == "discover_remote_system":
                if key == "IP":
                    args["ip_address"] = value
                elif key == "USER":
                    args["ssh_user"] = value
            elif tool_name == "create_vm":
                if key == "NAME":
                    args["vm_name"] = value
                elif key == "CORES":
                    args["cpu_cores"] = int(value)
                elif key == "MEMORY":
                    args["memory_gb"] = int(value)
                elif key == "DISK":
                    args["disk_size_gb"] = int(value)
                elif key == "NODE":
                    args["target_node"] = value
            
        return args
    
    
    async def _chat_with_tools(self, messages: List[Dict], model: str):
        """Non-streaming chat with tool execution."""
        # Implementation for non-streaming version
        return {"content": "Non-streaming chat not implemented yet"}
    
    async def _create_vm_handler(self, **kwargs) -> List[TextContent]:
        """Handle VM creation requests."""
        try:
            result = await create_vm_tool(**kwargs)
            
            if result.get("success"):
                message = f"✅ {result['message']}\n"
                message += f"VM ID: {result['vm_id']}\n"
                message += f"Node: {result['node']}\n"
                if result.get('ip_address'):
                    message += f"IP Address: {result['ip_address']}\n"
                    message += f"SSH Access: {result['ssh_access']}\n"
                message += f"Services: {', '.join(result.get('services', []))}"
            else:
                message = f"❌ {result['message']}\n"
                message += f"Error: {result.get('error', 'Unknown error')}"
            
            return [TextContent(type="text", text=message)]
            
        except Exception as e:
            error_message = f"❌ Failed to create VM: {str(e)}"
            return [TextContent(type="text", text=error_message)]
    
    async def _start_vm_handler(self, **kwargs) -> List[TextContent]:
        """Handle VM start requests."""
        try:
            result = await start_vm_tool(**kwargs)
            
            if result.get("success"):
                message = f"✅ {result['message']}\n"
                message += f"Node: {result['node']}"
            else:
                message = f"❌ {result['message']}"
            
            return [TextContent(type="text", text=message)]
            
        except Exception as e:
            error_message = f"❌ Failed to start VM: {str(e)}"
            return [TextContent(type="text", text=error_message)]
    
    async def _stop_vm_handler(self, **kwargs) -> List[TextContent]:
        """Handle VM stop requests."""
        try:
            result = await stop_vm_tool(**kwargs)
            
            if result.get("success"):
                message = f"✅ {result['message']}\n"
                message += f"Node: {result['node']}\n"
                message += f"Action: {result.get('action', 'stop')}"
            else:
                message = f"❌ {result['message']}"
            
            return [TextContent(type="text", text=message)]
            
        except Exception as e:
            error_message = f"❌ Failed to stop VM: {str(e)}"
            return [TextContent(type="text", text=error_message)]
    
    async def _delete_vm_handler(self, **kwargs) -> List[TextContent]:
        """Handle VM deletion requests."""
        try:
            result = await delete_vm_tool(**kwargs)
            
            if result.get("success"):
                message = f"✅ {result['message']}\n"
                message += f"Node: {result['node']}\n"
                message += f"Purged: {'Yes' if result.get('purged') else 'No'}"
            else:
                message = f"❌ {result['message']}"
            
            return [TextContent(type="text", text=message)]
            
        except Exception as e:
            error_message = f"❌ Failed to delete VM: {str(e)}"
            return [TextContent(type="text", text=error_message)]
    
    async def _get_vm_status_handler(self, **kwargs) -> List[TextContent]:
        """Handle VM status requests."""
        try:
            result = await get_vm_status_tool(**kwargs)
            
            if result.get("success"):
                message = f"VM {result['vm_id']} Status:\n"
                message += f"Name: {result.get('name', 'N/A')}\n"
                message += f"Node: {result['node']}\n"
                message += f"Status: {result['status']}\n"
                message += f"CPU Usage: {result.get('cpu', 0):.1%}\n"
                message += f"Memory: {result.get('memory', 0) / (1024**3):.1f}GB / {result.get('max_memory', 0) / (1024**3):.1f}GB\n"
                message += f"Disk: {result.get('disk', 0) / (1024**3):.1f}GB / {result.get('max_disk', 0) / (1024**3):.1f}GB\n"
                
                if result.get('uptime', 0) > 0:
                    uptime_hours = result['uptime'] / 3600
                    message += f"Uptime: {uptime_hours:.1f} hours\n"
                
                if result.get('ip_address'):
                    message += f"IP Address: {result['ip_address']}"
            else:
                message = f"❌ {result.get('message', 'Failed to get VM status')}\n"
                message += f"Error: {result.get('error', 'Unknown error')}"
            
            return [TextContent(type="text", text=message)]
            
        except Exception as e:
            error_message = f"❌ Failed to get VM status: {str(e)}"
            return [TextContent(type="text", text=error_message)]
    
    async def run_stdio(self):
        """Run the MCP server with stdio transport."""
        logger.info(f"Starting {self.name} with stdio transport...")
        await self.mcp.run_stdio_async()
    
    async def run_sse(self, mount_path: str | None = None):
        """Run the MCP server with SSE transport."""
        logger.info(f"Starting {self.name} with SSE transport on {self.mcp.settings.host}:{self.mcp.settings.port}...")
        await self.mcp.run_sse_async(mount_path=mount_path)
    
    async def run_streamable_http(self):
        """Run the MCP server with streamable HTTP transport."""
        logger.info(f"Starting {self.name} with streamable HTTP transport on {self.mcp.settings.host}:{self.mcp.settings.port}...")
        await self.mcp.run_streamable_http_async()
    
    async def run_chat_server(self):
        """Run the chat server separately on port 3001."""
        import uvicorn
        
        logger.info(f"Starting chat server on 0.0.0.0:3001...")
        
        chat_config = uvicorn.Config(
            self.chat_app,
            host="0.0.0.0",
            port=3001,
            log_level="info"
        )
        chat_server = uvicorn.Server(chat_config)
        await chat_server.serve()
    
    async def run_both_servers(self):
        """Run both MCP server and chat server concurrently."""
        import asyncio
        
        logger.info(f"Starting both MCP server (port 3000) and chat server (port 3001)...")
        
        # Start both servers concurrently
        mcp_task = asyncio.create_task(self.run_streamable_http())
        chat_task = asyncio.create_task(self.run_chat_server())
        
        # Wait for either to complete
        done, pending = await asyncio.wait(
            [mcp_task, chat_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel remaining tasks
        for task in pending:
            task.cancel()


async def main():
    """Main entry point for the MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    server = HomelabMCPServer()
    
    # Default to stdio transport for MCP compatibility
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())