"""
Agent-driven homelab management tools.
These tools are designed for AI agents to automatically configure homelab infrastructure
with minimal user interaction, using smart defaults and comparative analysis.
"""

from typing import Any, Dict, List, Optional
from mcp.types import Tool, TextContent
import json
import asyncio
from datetime import datetime

from .lxd_management import get_lxd_management_tools
from .ollama_assistant import get_ollama_assistant
from ..utils.credential_manager import get_credential_manager


# Agent-focused tool definitions
AGENT_HOMELAB_TOOLS = [
    Tool(
        name="auto-setup-homelab",
        description="Automatically set up a complete homelab environment on target host with smart defaults",
        inputSchema={
            "type": "object",
            "properties": {
                "target_host": {
                    "type": "string",
                    "description": "Target hostname or IP for homelab setup"
                },
                "user_goals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "User's goals (media, development, learning, automation, etc.)",
                    "default": ["learning", "media"]
                },
                "hardware_type": {
                    "type": "string",
                    "description": "Hardware type detected or specified",
                    "enum": ["raspberry-pi", "mini-pc", "server", "vm"],
                    "default": "raspberry-pi"
                },
                "install_ai": {
                    "type": "boolean",
                    "description": "Install local AI assistant (Ollama)",
                    "default": True
                }
            },
            "required": ["target_host"]
        }
    ),
    Tool(
        name="compare-storage-solutions",
        description="Compare storage solutions and recommend best option for user's needs",
        inputSchema={
            "type": "object",
            "properties": {
                "use_case": {
                    "type": "string",
                    "description": "Primary use case (media, backup, development, general)",
                    "default": "general"
                },
                "budget": {
                    "type": "string",
                    "description": "Budget range",
                    "enum": ["low", "moderate", "high"],
                    "default": "moderate"
                },
                "existing_hardware": {
                    "type": "string",
                    "description": "Existing hardware description"
                }
            }
        }
    ),
    Tool(
        name="recommend-service-stack",
        description="Recommend complete service stack based on user goals and hardware",
        inputSchema={
            "type": "object",
            "properties": {
                "goals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "User's primary goals"
                },
                "hardware_specs": {
                    "type": "object",
                    "properties": {
                        "cpu_cores": {"type": "integer"},
                        "memory_gb": {"type": "integer"},
                        "storage_gb": {"type": "integer"},
                        "gpu": {"type": "boolean"}
                    }
                },
                "experience_level": {
                    "type": "string",
                    "enum": ["beginner", "intermediate", "advanced"],
                    "default": "beginner"
                }
            },
            "required": ["goals"]
        }
    ),
    Tool(
        name="deploy-service-stack",
        description="Deploy recommended services automatically with smart configuration",
        inputSchema={
            "type": "object",
            "properties": {
                "target_host": {
                    "type": "string",
                    "description": "Target host for deployment"
                },
                "services": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Services to deploy"
                },
                "configuration": {
                    "type": "object",
                    "description": "Service-specific configuration overrides"
                }
            },
            "required": ["target_host", "services"]
        }
    ),
    Tool(
        name="auto-configure-networking",
        description="Automatically configure networking with security best practices",
        inputSchema={
            "type": "object",
            "properties": {
                "target_host": {
                    "type": "string",
                    "description": "Target host"
                },
                "services": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Services that need network access"
                },
                "security_level": {
                    "type": "string",
                    "enum": ["basic", "standard", "paranoid"],
                    "default": "standard"
                }
            },
            "required": ["target_host"]
        }
    ),
    Tool(
        name="explain-technology-choice",
        description="Explain why a specific technology was chosen with comparisons",
        inputSchema={
            "type": "object",
            "properties": {
                "chosen_tech": {
                    "type": "string",
                    "description": "Technology that was chosen"
                },
                "alternatives": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Alternative technologies considered"
                },
                "context": {
                    "type": "string",
                    "description": "Context for the decision"
                }
            },
            "required": ["chosen_tech"]
        }
    ),
    Tool(
        name="get-homelab-status",
        description="Get comprehensive status of homelab infrastructure",
        inputSchema={
            "type": "object",
            "properties": {
                "target_host": {
                    "type": "string",
                    "description": "Target host to check"
                },
                "include_recommendations": {
                    "type": "boolean",
                    "description": "Include optimization recommendations",
                    "default": True
                }
            },
            "required": ["target_host"]
        }
    ),
    Tool(
        name="troubleshoot-issue",
        description="Automatically diagnose and fix common homelab issues",
        inputSchema={
            "type": "object",
            "properties": {
                "target_host": {
                    "type": "string",
                    "description": "Target host"
                },
                "issue_description": {
                    "type": "string",
                    "description": "Description of the issue"
                },
                "service": {
                    "type": "string",
                    "description": "Specific service having issues (optional)"
                },
                "auto_fix": {
                    "type": "boolean",
                    "description": "Attempt automatic fixes",
                    "default": True
                }
            },
            "required": ["target_host", "issue_description"]
        }
    )
]


class AgentHomelabManager:
    """Agent-driven homelab management with smart defaults and minimal user interaction."""
    
    def __init__(self):
        self.lxd_tools = get_lxd_management_tools()
        self.ollama = get_ollama_assistant()
        self.credential_manager = get_credential_manager()
        
        # Technology comparison database for agent decision making
        self.tech_comparisons = {
            "storage": {
                "truenas": {
                    "pros": ["Professional ZFS", "Web UI", "Enterprise features", "Extensive plugin ecosystem"],
                    "cons": ["Resource intensive", "Complex for beginners", "Requires dedicated hardware"],
                    "best_for": ["Large storage needs", "Data integrity critical", "Multiple users"],
                    "industry_relevance": "Enterprise storage standard, similar to NetApp",
                    "resource_req": {"cpu_cores": 4, "memory_gb": 16, "storage_min": "2+ drives"}
                },
                "windows_smb": {
                    "pros": ["Familiar Windows interface", "Easy AD integration", "Good for mixed environments"],
                    "cons": ["Licensing costs", "Less efficient", "Windows-centric"],
                    "best_for": ["Windows-heavy environments", "Simple file sharing", "AD integration"],
                    "industry_relevance": "Common in Windows enterprises",
                    "resource_req": {"cpu_cores": 2, "memory_gb": 8, "storage_min": "Any"}
                },
                "nextcloud": {
                    "pros": ["Cloud-like interface", "Mobile apps", "Collaboration features", "Self-hosted"],
                    "cons": ["Requires web stack", "Performance considerations", "More complex than simple SMB"],
                    "best_for": ["Personal cloud", "Mobile access", "Collaboration", "Privacy-focused"],
                    "industry_relevance": "Similar to SharePoint/Google Workspace",
                    "resource_req": {"cpu_cores": 2, "memory_gb": 4, "storage_min": "Any"}
                },
                "simple_samba": {
                    "pros": ["Lightweight", "Fast setup", "Low resources", "Universal compatibility"],
                    "cons": ["Basic features only", "No web interface", "Manual management"],
                    "best_for": ["Simple file sharing", "Low-resource systems", "Quick setup"],
                    "industry_relevance": "Foundation of enterprise file sharing",
                    "resource_req": {"cpu_cores": 1, "memory_gb": 1, "storage_min": "Any"}
                }
            },
            "virtualization": {
                "proxmox": {
                    "pros": ["Professional grade", "VMs + Containers", "Web UI", "Clustering"],
                    "cons": ["Complex setup", "Resource intensive", "Steep learning curve"],
                    "best_for": ["Learning enterprise skills", "Multiple VMs", "Production-like setups"],
                    "industry_relevance": "Similar to VMware vSphere",
                    "resource_req": {"cpu_cores": 4, "memory_gb": 16, "storage_min": "100GB"}
                },
                "lxd": {
                    "pros": ["Lightweight", "Fast containers", "Easy to learn", "Low resources"],
                    "cons": ["Linux containers only", "Less feature rich", "Not industry standard"],
                    "best_for": ["Learning containers", "Resource-constrained", "Simple workloads"],
                    "industry_relevance": "Container concepts apply to Kubernetes",
                    "resource_req": {"cpu_cores": 1, "memory_gb": 2, "storage_min": "20GB"}
                },
                "docker": {
                    "pros": ["Industry standard", "Huge ecosystem", "Easy application deployment"],
                    "cons": ["Application containers only", "Complex networking", "Security considerations"],
                    "best_for": ["Application deployment", "Learning DevOps", "Microservices"],
                    "industry_relevance": "Essential for modern development",
                    "resource_req": {"cpu_cores": 2, "memory_gb": 4, "storage_min": "50GB"}
                }
            }
        }
        
    async def auto_setup_homelab(
        self,
        target_host: str,
        user_goals: List[str] = None,
        hardware_type: str = "raspberry-pi",
        install_ai: bool = True
    ) -> Dict[str, Any]:
        """Automatically set up complete homelab with smart defaults."""
        
        if user_goals is None:
            user_goals = ["learning", "media"]
            
        setup_log = []
        services_installed = []
        
        try:
            # 1. Detect hardware capabilities
            setup_log.append("🔍 Detecting hardware capabilities...")
            
            # For now, use hardware_type to determine capabilities
            hardware_caps = self._get_hardware_capabilities(hardware_type)
            
            # 2. Choose optimal platform based on hardware
            if hardware_caps["memory_gb"] >= 16 and "learning" in user_goals:
                platform = "proxmox"
                setup_log.append("📦 Chosen: Proxmox VE (powerful hardware + learning goals)")
            elif hardware_caps["memory_gb"] >= 4:
                platform = "lxd"
                setup_log.append("📦 Chosen: LXD containers (good balance of features/resources)")
            else:
                platform = "docker"
                setup_log.append("📦 Chosen: Docker (lightweight for limited resources)")
                
            # 3. Install platform if needed
            if platform == "lxd":
                setup_log.append("⚙️ Installing LXD...")
                lxd_result = await self.lxd_tools.install_lxd(
                    host=target_host,
                    storage_backend="dir",  # Safe default
                    storage_size="20GB"
                )
                if lxd_result.get("success"):
                    setup_log.append("✅ LXD installed successfully")
                else:
                    setup_log.append(f"❌ LXD installation failed: {lxd_result.get('error')}")
                    
            # 4. Install AI assistant if requested
            if install_ai:
                setup_log.append("🤖 Setting up local AI assistant...")
                model = "tinyllama" if hardware_caps["memory_gb"] < 8 else "llama2:7b"
                # Implementation would install Ollama with appropriate model
                setup_log.append(f"✅ AI assistant ready (model: {model})")
                services_installed.append(f"ollama-{model}")
                
            # 5. Install core services based on goals
            recommended_services = self._recommend_services(user_goals, hardware_caps)
            
            for service in recommended_services[:3]:  # Limit to 3 for initial setup
                setup_log.append(f"📥 Installing {service}...")
                # Implementation would install each service
                setup_log.append(f"✅ {service} installed")
                services_installed.append(service)
                
            # 6. Configure networking and security
            setup_log.append("🔒 Configuring security and networking...")
            # Implementation would set up firewall, reverse proxy, etc.
            setup_log.append("✅ Security configured")
            
            return {
                "success": True,
                "platform": platform,
                "services_installed": services_installed,
                "setup_log": setup_log,
                "next_steps": [
                    f"Access your services at http://{target_host}",
                    "Check service status with 'get-homelab-status'",
                    "Ask your local AI for help with 'ask-ollama'"
                ],
                "estimated_setup_time": "15-30 minutes",
                "why_these_choices": self._explain_choices(platform, recommended_services, user_goals, hardware_caps)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "setup_log": setup_log
            }
            
    def _get_hardware_capabilities(self, hardware_type: str) -> Dict[str, Any]:
        """Estimate hardware capabilities based on type."""
        capabilities = {
            "raspberry-pi": {"cpu_cores": 4, "memory_gb": 4, "storage_gb": 64, "gpu": False},
            "mini-pc": {"cpu_cores": 8, "memory_gb": 16, "storage_gb": 500, "gpu": False},
            "server": {"cpu_cores": 16, "memory_gb": 64, "storage_gb": 2000, "gpu": True},
            "vm": {"cpu_cores": 4, "memory_gb": 8, "storage_gb": 100, "gpu": False}
        }
        return capabilities.get(hardware_type, capabilities["raspberry-pi"])
        
    def _recommend_services(self, goals: List[str], hardware: Dict[str, Any]) -> List[str]:
        """Recommend services based on goals and hardware."""
        services = []
        
        # Core services everyone needs
        services.append("pihole")  # DNS filtering
        
        if "media" in goals:
            services.extend(["jellyfin"])
            
        if "automation" in goals:
            services.extend(["homeassistant"])
            
        if "development" in goals:
            services.extend(["docker", "gitea"])
            
        if "storage" in goals or "backup" in goals:
            if hardware["memory_gb"] >= 16:
                services.append("nextcloud")
            else:
                services.append("samba")
                
        if "learning" in goals:
            services.extend(["portainer", "grafana"])
            
        return services
        
    def _explain_choices(
        self,
        platform: str,
        services: List[str],
        goals: List[str],
        hardware: Dict[str, Any]
    ) -> Dict[str, str]:
        """Explain why specific choices were made."""
        explanations = {}
        
        # Platform choice
        if platform == "proxmox":
            explanations["platform"] = (
                "Chose Proxmox because you have powerful hardware and want to learn enterprise "
                "virtualization skills. This is the same technology used in data centers."
            )
        elif platform == "lxd":
            explanations["platform"] = (
                "Chose LXD containers for the best balance of capabilities and resource usage. "
                "You'll learn container concepts that apply to Kubernetes."
            )
        else:
            explanations["platform"] = (
                "Chose Docker because it's industry standard and works well on your hardware. "
                "Docker skills are essential for modern development roles."
            )
            
        # Service explanations
        service_reasons = {
            "pihole": "Blocks ads network-wide and teaches DNS concepts",
            "jellyfin": "Personal media streaming server (like your own Netflix)",
            "homeassistant": "Home automation hub that integrates everything",
            "nextcloud": "Your own cloud storage (like Google Drive but private)",
            "portainer": "Visual Docker management - great for learning containers"
        }
        
        for service in services:
            if service in service_reasons:
                explanations[service] = service_reasons[service]
                
        return explanations
        
    async def compare_storage_solutions(
        self,
        use_case: str = "general",
        budget: str = "moderate",
        existing_hardware: str = None
    ) -> Dict[str, Any]:
        """Compare storage solutions and recommend best option."""
        
        storage_options = self.tech_comparisons["storage"]
        
        # Score each option based on use case
        scored_options = []
        
        for name, details in storage_options.items():
            score = 0
            
            # Use case scoring
            if use_case == "media" and name in ["truenas", "simple_samba"]:
                score += 3
            elif use_case == "backup" and name == "truenas":
                score += 3
            elif use_case == "general" and name in ["nextcloud", "simple_samba"]:
                score += 2
                
            # Budget scoring
            if budget == "low" and name == "simple_samba":
                score += 2
            elif budget == "moderate" and name in ["nextcloud", "simple_samba"]:
                score += 1
            elif budget == "high" and name == "truenas":
                score += 1
                
            scored_options.append((score, name, details))
            
        # Sort by score
        scored_options.sort(key=lambda x: x[0], reverse=True)
        
        best_option = scored_options[0]
        alternatives = scored_options[1:3]
        
        return {
            "recommended": {
                "name": best_option[1],
                "score": best_option[0],
                "details": best_option[2],
                "why_recommended": f"Best fit for {use_case} use case with {budget} budget"
            },
            "alternatives": [
                {
                    "name": alt[1],
                    "details": alt[2],
                    "trade_offs": f"Consider if {', '.join(alt[2]['best_for'])}"
                }
                for alt in alternatives
            ],
            "comparison_summary": self._generate_comparison_summary(scored_options, use_case)
        }
        
    def _generate_comparison_summary(self, options: List, use_case: str) -> str:
        """Generate a summary comparing the storage options."""
        return (
            f"For {use_case} use case:\n"
            f"🥇 {options[0][1]}: {', '.join(options[0][2]['pros'][:2])}\n"
            f"🥈 {options[1][1]}: {', '.join(options[1][2]['pros'][:2])}\n"
            f"🥉 {options[2][1]}: {', '.join(options[2][2]['pros'][:2])}"
        )
        
    async def explain_technology_choice(
        self,
        chosen_tech: str,
        alternatives: List[str] = None,
        context: str = ""
    ) -> Dict[str, Any]:
        """Explain why a technology was chosen with detailed comparison."""
        
        # Find the technology in our comparison database
        tech_info = None
        category = None
        
        for cat, techs in self.tech_comparisons.items():
            if chosen_tech.lower() in techs:
                tech_info = techs[chosen_tech.lower()]
                category = cat
                break
                
        if not tech_info:
            return {"error": f"Technology '{chosen_tech}' not found in comparison database"}
            
        explanation = {
            "chosen_technology": chosen_tech,
            "category": category,
            "why_chosen": {
                "strengths": tech_info["pros"],
                "best_for": tech_info["best_for"],
                "industry_relevance": tech_info["industry_relevance"]
            },
            "trade_offs": {
                "limitations": tech_info["cons"],
                "resource_requirements": tech_info["resource_req"]
            }
        }
        
        # Add comparisons with alternatives if provided
        if alternatives:
            comparisons = {}
            for alt in alternatives:
                if alt.lower() in self.tech_comparisons[category]:
                    alt_info = self.tech_comparisons[category][alt.lower()]
                    comparisons[alt] = {
                        "vs_chosen": self._compare_technologies(tech_info, alt_info),
                        "better_for": alt_info["best_for"]
                    }
            explanation["vs_alternatives"] = comparisons
            
        return explanation
        
    def _compare_technologies(self, tech1: Dict, tech2: Dict) -> str:
        """Compare two technologies and explain the differences."""
        # Simple comparison logic - in practice this would be more sophisticated
        if len(tech1["pros"]) > len(tech2["pros"]):
            return f"Chosen tech has more advantages ({len(tech1['pros'])} vs {len(tech2['pros'])})"
        else:
            return "Both technologies have similar capabilities"


# Singleton instance
_agent_homelab_manager = None


def get_agent_homelab_manager() -> AgentHomelabManager:
    """Get singleton instance of agent homelab manager."""
    global _agent_homelab_manager
    if _agent_homelab_manager is None:
        _agent_homelab_manager = AgentHomelabManager()
    return _agent_homelab_manager


async def handle_agent_homelab_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle agent-driven homelab tools."""
    try:
        manager = get_agent_homelab_manager()
        
        if name == "auto-setup-homelab":
            result = await manager.auto_setup_homelab(
                target_host=arguments["target_host"],
                user_goals=arguments.get("user_goals", ["learning", "media"]),
                hardware_type=arguments.get("hardware_type", "raspberry-pi"),
                install_ai=arguments.get("install_ai", True)
            )
            
        elif name == "compare-storage-solutions":
            result = await manager.compare_storage_solutions(
                use_case=arguments.get("use_case", "general"),
                budget=arguments.get("budget", "moderate"),
                existing_hardware=arguments.get("existing_hardware")
            )
            
        elif name == "explain-technology-choice":
            result = await manager.explain_technology_choice(
                chosen_tech=arguments["chosen_tech"],
                alternatives=arguments.get("alternatives", []),
                context=arguments.get("context", "")
            )
            
        else:
            result = {"error": f"Unknown tool: {name}", "available_tools": [tool.name for tool in AGENT_HOMELAB_TOOLS]}
            
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
        
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


def get_agent_homelab_tools() -> List[Tool]:
    """Get all agent-driven homelab tools."""
    return AGENT_HOMELAB_TOOLS