"""
Homelab wizard and AI assistant MCP tool definitions.
Provides beginner-friendly guidance and local AI integration.
"""

from typing import Any, Dict, List
from mcp.types import Tool, TextContent
import json

from .homelab_wizard import get_homelab_wizard
from .ollama_assistant import get_ollama_assistant
from .lxd_management import get_lxd_management_tools


# Tool definitions
HOMELAB_TOOLS = [
    Tool(
        name="homelab-interview",
        description="Start an interactive interview to help plan your homelab journey",
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "Unique identifier for the user session",
                    "default": "default"
                }
            }
        }
    ),
    Tool(
        name="homelab-answer",
        description="Process answer to homelab interview question",
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "User session identifier",
                    "default": "default"
                },
                "question_id": {
                    "type": "string",
                    "description": "ID of the question being answered"
                },
                "answer": {
                    "type": ["string", "array"],
                    "description": "User's answer (string or array for multiple choice)"
                }
            },
            "required": ["question_id", "answer"]
        }
    ),
    Tool(
        name="explain-concept",
        description="Get beginner-friendly explanation of technical concepts",
        inputSchema={
            "type": "object",
            "properties": {
                "concept": {
                    "type": "string",
                    "description": "Technical concept to explain (e.g., 'virtualization', 'containers', 'reverse proxy')"
                }
            },
            "required": ["concept"]
        }
    ),
    Tool(
        name="compare-technologies",
        description="Compare two technologies with pros, cons, and recommendations",
        inputSchema={
            "type": "object",
            "properties": {
                "option1": {
                    "type": "string",
                    "description": "First technology option"
                },
                "option2": {
                    "type": "string",
                    "description": "Second technology option"
                },
                "context": {
                    "type": "string",
                    "description": "Context for comparison",
                    "default": "general homelab use"
                }
            },
            "required": ["option1", "option2"]
        }
    ),
    Tool(
        name="setup-ollama",
        description="Get personalized guide for setting up Ollama AI assistant",
        inputSchema={
            "type": "object",
            "properties": {
                "hardware_type": {
                    "type": "string",
                    "description": "Type of hardware (raspberry-pi, proxmox, server, desktop)"
                },
                "memory_gb": {
                    "type": "integer",
                    "description": "Available RAM in GB",
                    "default": 8
                },
                "gpu_available": {
                    "type": "boolean",
                    "description": "Whether GPU is available",
                    "default": False
                },
                "target_host": {
                    "type": "string",
                    "description": "Target hostname or IP for Ollama installation",
                    "default": "localhost"
                }
            },
            "required": ["hardware_type"]
        }
    ),
    Tool(
        name="check-ollama",
        description="Check if Ollama is running and list available models",
        inputSchema={
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "Ollama host address",
                    "default": "localhost"
                },
                "port": {
                    "type": "integer",
                    "description": "Ollama API port",
                    "default": 11434
                }
            }
        }
    ),
    Tool(
        name="suggest-ollama-model",
        description="Get model recommendations based on use case and hardware",
        inputSchema={
            "type": "object",
            "properties": {
                "use_case": {
                    "type": "string",
                    "description": "What you want to use the AI for"
                },
                "available_memory": {
                    "type": "integer",
                    "description": "Available RAM in GB"
                },
                "prefer_fast": {
                    "type": "boolean",
                    "description": "Prefer faster, smaller models",
                    "default": True
                }
            },
            "required": ["use_case", "available_memory"]
        }
    ),
    Tool(
        name="ask-ollama",
        description="Ask a question to your local Ollama AI assistant",
        inputSchema={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Your homelab question"
                },
                "model": {
                    "type": "string",
                    "description": "Ollama model to use",
                    "default": "llama2:7b"
                },
                "host": {
                    "type": "string",
                    "description": "Ollama host address",
                    "default": "localhost"
                },
                "port": {
                    "type": "integer",
                    "description": "Ollama API port",
                    "default": 11434
                },
                "context": {
                    "type": "object",
                    "description": "Context about your setup",
                    "properties": {
                        "hardware": {"type": "string"},
                        "experience": {"type": "string"},
                        "goals": {"type": "string"}
                    }
                }
            },
            "required": ["question"]
        }
    ),
    Tool(
        name="generate-ollama-compose",
        description="Generate Docker Compose file for Ollama with web UI",
        inputSchema={
            "type": "object",
            "properties": {
                "port": {
                    "type": "integer",
                    "description": "Ollama API port",
                    "default": 11434
                },
                "webui_port": {
                    "type": "integer",
                    "description": "Web UI port",
                    "default": 3000
                },
                "gpu_support": {
                    "type": "boolean",
                    "description": "Enable GPU support",
                    "default": False
                }
            }
        }
    ),
    Tool(
        name="setup-service-wizard",
        description="Interactive wizard to set up a specific homelab service",
        inputSchema={
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service to set up",
                    "enum": ["pihole", "nextcloud", "jellyfin", "homeassistant", "docker", "ollama"]
                },
                "target_host": {
                    "type": "string",
                    "description": "Target host for installation"
                },
                "experience_level": {
                    "type": "string",
                    "description": "User's experience level",
                    "enum": ["beginner", "intermediate", "advanced"],
                    "default": "beginner"
                }
            },
            "required": ["service", "target_host"]
        }
    )
]


async def handle_homelab_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle homelab wizard and AI assistant tools."""
    try:
        wizard = get_homelab_wizard()
        ollama = get_ollama_assistant()
        
        if name == "homelab-interview":
            result = await wizard.start_interview(
                user_id=arguments.get("user_id", "default")
            )
            
        elif name == "homelab-answer":
            result = await wizard.process_answer(
                user_id=arguments.get("user_id", "default"),
                question_id=arguments["question_id"],
                answer=arguments["answer"]
            )
            
        elif name == "explain-concept":
            result = await wizard.explain_concept(
                concept=arguments["concept"]
            )
            
        elif name == "compare-technologies":
            result = await wizard.compare_options(
                option1=arguments["option1"],
                option2=arguments["option2"],
                context=arguments.get("context", "general homelab use")
            )
            
        elif name == "setup-ollama":
            # Create hardware info dict
            hardware_info = {
                "type": arguments["hardware_type"],
                "memory_gb": arguments.get("memory_gb", 8),
                "gpu": arguments.get("gpu_available", False)
            }
            
            # Generate setup guide
            guide = await ollama.generate_setup_guide(
                hardware_type=arguments["hardware_type"],
                available_memory=arguments.get("memory_gb", 8),
                gpu_available=arguments.get("gpu_available", False)
            )
            
            # Format for display
            result = {
                "setup_guide": {
                    "hardware": guide.hardware_type,
                    "steps": guide.steps,
                    "recommended_models": [
                        {
                            "name": m.name,
                            "size": m.size,
                            "description": m.description,
                            "use_case": m.use_case
                        }
                        for m in guide.model_recommendations
                    ],
                    "tips": guide.tips
                },
                "target_host": arguments.get("target_host", "localhost"),
                "note": f"Install on {arguments.get('target_host', 'localhost')} for best performance"
            }
            
        elif name == "check-ollama":
            result = await ollama.check_ollama_status(
                host=arguments.get("host", "localhost"),
                port=arguments.get("port", 11434)
            )
            
        elif name == "suggest-ollama-model":
            result = await ollama.suggest_model(
                use_case=arguments["use_case"],
                available_memory=arguments["available_memory"],
                prefer_fast=arguments.get("prefer_fast", True)
            )
            
        elif name == "ask-ollama":
            # Create context-aware prompt
            context = arguments.get("context", {})
            prompt = await ollama.create_homelab_prompt(
                question=arguments["question"],
                context=context
            )
            
            # Query Ollama
            response = await ollama.query_ollama(
                prompt=prompt,
                model=arguments.get("model", "llama2:7b"),
                host=arguments.get("host", "localhost"),
                port=arguments.get("port", 11434)
            )
            
            result = {
                "question": arguments["question"],
                "answer": response,
                "model": arguments.get("model", "llama2:7b"),
                "host": arguments.get("host", "localhost")
            }
            
        elif name == "generate-ollama-compose":
            compose_content = ollama.generate_ollama_compose(arguments)
            result = {
                "docker_compose": compose_content,
                "filename": "docker-compose.ollama.yml",
                "instructions": [
                    "Save this as docker-compose.yml",
                    "Run: docker-compose up -d",
                    f"Access Ollama API at http://localhost:{arguments.get('port', 11434)}",
                    f"Access Web UI at http://localhost:{arguments.get('webui_port', 3000)}"
                ]
            }
            
        elif name == "setup-service-wizard":
            # Get service recommendation from wizard
            service_info = wizard.service_catalog.get(arguments["service"])
            
            if not service_info:
                result = {"error": f"Unknown service: {arguments['service']}"}
            else:
                # Check if prerequisites are met
                lxd_tools = get_lxd_management_tools()
                
                # For LXD-based services, check LXD status
                if arguments["service"] in ["pihole", "nextcloud", "jellyfin"]:
                    lxd_status = await lxd_tools.check_lxd_installed(
                        host=arguments["target_host"],
                        ssh_user=arguments.get("ssh_user", "pi")
                    )
                    
                    if not lxd_status.get("installed"):
                        result = {
                            "service": arguments["service"],
                            "status": "prerequisites_missing",
                            "missing": "LXD not installed",
                            "recommendation": "Run 'install-lxd' first to set up container platform",
                            "service_info": {
                                "name": service_info.name,
                                "description": service_info.description,
                                "difficulty": service_info.difficulty
                            }
                        }
                    else:
                        result = {
                            "service": arguments["service"],
                            "status": "ready_to_install",
                            "service_info": {
                                "name": service_info.name,
                                "description": service_info.description,
                                "difficulty": service_info.difficulty,
                                "why_useful": service_info.why_useful
                            },
                            "next_steps": [
                                f"Create container: create-lxd-container name={arguments['service']}-server",
                                f"Install service: install-service-lxd container_name={arguments['service']}-server service={arguments['service']}"
                            ]
                        }
                else:
                    # Non-LXD services
                    result = {
                        "service": arguments["service"],
                        "service_info": {
                            "name": service_info.name,
                            "description": service_info.description,
                            "prerequisites": service_info.prerequisites
                        }
                    }
                    
        else:
            result = {"error": f"Unknown tool: {name}"}
            
        # Format result
        if isinstance(result, dict):
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        else:
            return [TextContent(type="text", text=str(result))]
            
    except Exception as e:
        error_result = {
            "error": str(e),
            "tool": name,
            "arguments": arguments
        }
        return [TextContent(
            type="text",
            text=json.dumps(error_result, indent=2)
        )]


def get_homelab_tools() -> List[Tool]:
    """Get all homelab wizard and AI assistant tools."""
    return HOMELAB_TOOLS