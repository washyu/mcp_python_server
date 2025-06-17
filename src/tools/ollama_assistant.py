"""
Ollama AI assistant integration for local homelab guidance.
Provides free, private AI assistance using locally-hosted models.
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator, Union
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class OllamaModel:
    """Information about an available Ollama model."""
    name: str
    size: str
    description: str
    use_case: str
    memory_required: str
    good_for_beginners: bool = True


@dataclass
class OllamaSetupGuide:
    """Step-by-step guide for setting up Ollama."""
    hardware_type: str
    steps: List[Dict[str, str]]
    model_recommendations: List[OllamaModel]
    tips: List[str]


class OllamaAssistant:
    """Manages Ollama setup and integration for homelab assistance."""
    
    def __init__(self):
        self.ollama_host: Optional[str] = None
        self.ollama_port: int = 11434
        self.current_model: Optional[str] = None
        self.model_catalog = self._initialize_model_catalog()
        
    def _initialize_model_catalog(self) -> Dict[str, OllamaModel]:
        """Initialize catalog of Ollama models suitable for homelab assistance."""
        return {
            "deepseek-r1:8b": OllamaModel(
                name="deepseek-r1:8b",
                size="4.7GB",
                description="DeepSeek's reasoning model - excellent for complex problem solving",
                use_case="Complex homelab planning, multi-step troubleshooting, technical reasoning",
                memory_required="8GB RAM minimum",
                good_for_beginners=True
            ),
            "llama2:7b": OllamaModel(
                name="llama2:7b",
                size="3.8GB",
                description="Meta's Llama 2 model - great general purpose assistant",
                use_case="General homelab guidance, explaining concepts, troubleshooting",
                memory_required="8GB RAM minimum",
                good_for_beginners=True
            ),
            "mistral:7b": OllamaModel(
                name="mistral:7b",
                size="4.1GB",
                description="Fast and efficient model, good for technical tasks",
                use_case="Code generation, technical explanations, configuration help",
                memory_required="8GB RAM minimum",
                good_for_beginners=True
            ),
            "llama2:13b": OllamaModel(
                name="llama2:13b",
                size="7.4GB",
                description="Larger model with better reasoning capabilities",
                use_case="Complex troubleshooting, detailed explanations, planning",
                memory_required="16GB RAM recommended",
                good_for_beginners=False
            ),
            "codellama:7b": OllamaModel(
                name="codellama:7b",
                size="3.8GB",
                description="Specialized for code and configuration files",
                use_case="Writing scripts, Docker configs, automation code",
                memory_required="8GB RAM minimum",
                good_for_beginners=True
            ),
            "phi": OllamaModel(
                name="phi",
                size="1.6GB",
                description="Microsoft's tiny but capable model",
                use_case="Quick responses, low-resource systems, Raspberry Pi",
                memory_required="4GB RAM minimum",
                good_for_beginners=True
            ),
            "tinyllama": OllamaModel(
                name="tinyllama",
                size="638MB",
                description="Ultra-lightweight model for minimal hardware",
                use_case="Basic Q&A, simple guidance, very low resource use",
                memory_required="2GB RAM minimum",
                good_for_beginners=True
            )
        }
        
    async def generate_setup_guide(
        self,
        hardware_type: str,
        available_memory: int,
        gpu_available: bool = False
    ) -> OllamaSetupGuide:
        """Generate personalized Ollama setup guide based on hardware."""
        
        # Base installation steps
        if "raspberry" in hardware_type.lower():
            steps = [
                {
                    "step": "1",
                    "action": "Install Ollama on Raspberry Pi",
                    "command": "curl -fsSL https://ollama.ai/install.sh | sh",
                    "note": "This installs Ollama system-wide with automatic startup"
                },
                {
                    "step": "2",
                    "action": "Start Ollama service",
                    "command": "sudo systemctl start ollama",
                    "note": "Ollama will now run in the background"
                },
                {
                    "step": "3",
                    "action": "Pull a lightweight model",
                    "command": "ollama pull tinyllama",
                    "note": "TinyLlama is perfect for Pi with only 638MB size"
                },
                {
                    "step": "4",
                    "action": "Test the model",
                    "command": "ollama run tinyllama 'Hello, can you help with my homelab?'",
                    "note": "You should see a response from your local AI!"
                },
                {
                    "step": "5",
                    "action": "Enable remote access (optional)",
                    "command": "OLLAMA_HOST=0.0.0.0 ollama serve",
                    "note": "This allows other devices to use your Ollama instance"
                }
            ]
            
            # Model recommendations based on Pi memory
            if available_memory >= 8:
                models = [
                    self.model_catalog["phi"],
                    self.model_catalog["tinyllama"],
                    self.model_catalog["mistral:7b"]
                ]
            else:
                models = [
                    self.model_catalog["tinyllama"],
                    self.model_catalog["phi"]
                ]
                
            tips = [
                "Start with TinyLlama to ensure everything works",
                "Monitor memory usage with 'htop' while running",
                "Consider adding swap space for larger models",
                "USB3 SSD greatly improves model loading times"
            ]
            
        elif "proxmox" in hardware_type.lower() or "server" in hardware_type.lower():
            steps = [
                {
                    "step": "1",
                    "action": "Create a dedicated VM or LXC container",
                    "command": "Create Ubuntu 22.04 VM with 8GB+ RAM",
                    "note": "Dedicated resources ensure consistent performance"
                },
                {
                    "step": "2",
                    "action": "Install Ollama in the VM",
                    "command": "curl -fsSL https://ollama.ai/install.sh | sh",
                    "note": "Same installation process as bare metal"
                },
                {
                    "step": "3",
                    "action": "Configure for network access",
                    "command": "sudo systemctl edit ollama.service",
                    "note": "Add: Environment='OLLAMA_HOST=0.0.0.0'"
                },
                {
                    "step": "4",
                    "action": "Pull recommended models",
                    "command": "ollama pull llama2:7b mistral:7b",
                    "note": "These provide excellent capability/size balance"
                },
                {
                    "step": "5",
                    "action": "Set up reverse proxy (optional)",
                    "command": "Configure nginx to proxy port 11434",
                    "note": "Adds SSL and better access control"
                }
            ]
            
            # More models available with server hardware
            models = [
                self.model_catalog["llama2:7b"],
                self.model_catalog["mistral:7b"],
                self.model_catalog["codellama:7b"]
            ]
            
            if available_memory >= 16:
                models.append(self.model_catalog["llama2:13b"])
                
            tips = [
                "GPU passthrough dramatically improves performance",
                "Consider running multiple models for different tasks",
                "Set up model preloading for faster responses",
                "Monitor disk space - models can be large"
            ]
            
        else:  # Generic Linux/Docker setup
            steps = [
                {
                    "step": "1",
                    "action": "Install via Docker (recommended)",
                    "command": "docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama",
                    "note": "Docker provides easy management and updates"
                },
                {
                    "step": "2",
                    "action": "Pull your first model",
                    "command": "docker exec -it ollama ollama pull llama2:7b",
                    "note": "This downloads and prepares the model"
                },
                {
                    "step": "3",
                    "action": "Test the setup",
                    "command": "curl http://localhost:11434/api/generate -d '{\"model\":\"llama2:7b\",\"prompt\":\"Hello\"}'",
                    "note": "Should return a JSON response with generated text"
                }
            ]
            
            models = [self.model_catalog["llama2:7b"], self.model_catalog["phi"]]
            tips = ["Docker Compose makes management easier", "Consider GPU support for better performance"]
            
        return OllamaSetupGuide(
            hardware_type=hardware_type,
            steps=steps,
            model_recommendations=models,
            tips=tips
        )
        
    async def check_ollama_status(self, host: str = "localhost", port: int = 11434) -> Dict[str, Any]:
        """Check if Ollama is running and accessible."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://{host}:{port}/api/tags") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = data.get("models", [])
                        
                        return {
                            "status": "running",
                            "host": host,
                            "port": port,
                            "available_models": [m["name"] for m in models],
                            "total_size": sum(m.get("size", 0) for m in models) / 1e9,  # GB
                            "model_count": len(models)
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"Ollama API returned status {resp.status}"
                        }
        except aiohttp.ClientConnectorError:
            return {
                "status": "not_running",
                "error": "Cannot connect to Ollama. Is it installed and running?",
                "help": "Run 'systemctl status ollama' to check service status"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
            
    async def suggest_model(
        self,
        use_case: str,
        available_memory: int,
        prefer_fast: bool = True
    ) -> Dict[str, Any]:
        """Suggest best Ollama model for specific use case."""
        
        # Filter models by memory requirements
        suitable_models = []
        for model_name, model in self.model_catalog.items():
            required_gb = int(model.memory_required.split("GB")[0])
            if available_memory >= required_gb:
                suitable_models.append(model)
                
        if not suitable_models:
            return {
                "error": "No models suitable for available memory",
                "suggestion": "Consider adding more RAM or using cloud services",
                "minimum_model": self.model_catalog["tinyllama"]
            }
            
        # Score models based on use case
        use_case_lower = use_case.lower()
        scored_models = []
        
        for model in suitable_models:
            score = 0
            
            # Match use case
            if "code" in use_case_lower and "code" in model.use_case.lower():
                score += 3
            elif "general" in use_case_lower and "general" in model.use_case.lower():
                score += 3
            elif "troubleshoot" in use_case_lower and "troubleshoot" in model.use_case.lower():
                score += 2
                
            # Prefer faster models if requested
            if prefer_fast and "GB" in model.size:
                size_gb = float(model.size.replace("GB", ""))
                if size_gb < 2:
                    score += 2
                elif size_gb < 5:
                    score += 1
                    
            # Beginner friendly bonus
            if model.good_for_beginners:
                score += 1
                
            scored_models.append((score, model))
            
        # Sort by score
        scored_models.sort(key=lambda x: x[0], reverse=True)
        
        best_model = scored_models[0][1]
        alternatives = [m[1] for m in scored_models[1:3]]
        
        return {
            "recommended": {
                "name": best_model.name,
                "reason": best_model.use_case,
                "size": best_model.size,
                "pull_command": f"ollama pull {best_model.name}"
            },
            "alternatives": [
                {
                    "name": alt.name,
                    "reason": f"Alternative: {alt.description}",
                    "size": alt.size
                }
                for alt in alternatives
            ],
            "tip": "You can have multiple models installed and switch between them"
        }
        
    async def create_homelab_prompt(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create an optimized prompt for homelab assistance."""
        
        base_prompt = f"""You are a friendly homelab assistant helping someone with their personal IT lab setup. 
Keep responses practical and beginner-friendly. Focus on open-source solutions.

User's setup context:
- Hardware: {context.get('hardware', 'Not specified')}
- Experience: {context.get('experience', 'Beginner')}
- Goals: {context.get('goals', 'Learning and self-hosting')}

Question: {question}

Provide a helpful, concise response with practical next steps."""

        return base_prompt
        
    async def query_ollama(
        self,
        prompt: str,
        model: str = "llama2:7b",
        host: str = "localhost",
        port: int = 11434,
        stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Query Ollama model with a prompt."""
        
        url = f"http://{host}:{port}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream
        }
        
        try:
            if stream:
                async def response_generator():
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, json=payload) as resp:
                            async for line in resp.content:
                                if line:
                                    try:
                                        data = json.loads(line.decode('utf-8'))
                                        if "response" in data and data["response"]:
                                            yield data["response"]
                                    except json.JSONDecodeError:
                                        continue  # Skip invalid JSON lines
                return response_generator()
            else:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload) as resp:
                        data = await resp.json()
                        return data.get("response", "")
                        
        except Exception as e:
            logger.error(f"Failed to query Ollama: {e}")
            return f"Error querying AI: {str(e)}"
            
    async def setup_homelab_assistant(
        self,
        hardware_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Complete setup process for Ollama-based homelab assistant."""
        
        # Check current status
        status = await self.check_ollama_status()
        
        if status["status"] == "running":
            return {
                "status": "already_setup",
                "message": "Ollama is already running!",
                "available_models": status.get("available_models", []),
                "next_step": "You can start asking questions or install more models"
            }
            
        # Generate setup guide
        guide = await self.generate_setup_guide(
            hardware_type=hardware_info.get("type", "generic"),
            available_memory=hardware_info.get("memory_gb", 8),
            gpu_available=hardware_info.get("gpu", False)
        )
        
        # Suggest initial model
        model_suggestion = await self.suggest_model(
            use_case="general homelab assistance",
            available_memory=hardware_info.get("memory_gb", 8),
            prefer_fast=True
        )
        
        return {
            "status": "needs_setup",
            "setup_guide": guide,
            "recommended_model": model_suggestion["recommended"],
            "estimated_time": "15-30 minutes including model download",
            "benefits": [
                "Free AI assistance forever",
                "Complete privacy - runs locally",
                "Learn about AI/ML as bonus",
                "Can be shared with family"
            ]
        }
        
    def generate_ollama_compose(self, config: Dict[str, Any]) -> str:
        """Generate Docker Compose file for Ollama setup."""
        
        compose = f"""version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "{config.get('port', 11434)}:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped
    environment:
      - OLLAMA_HOST=0.0.0.0
"""
        
        # Add GPU support if available
        if config.get("gpu_support"):
            compose += """    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
"""
        
        compose += """
  ollama-webui:
    image: ghcr.io/ollama-webui/ollama-webui:main
    container_name: ollama-webui
    ports:
      - "{config.get('webui_port', 3000)}:8080"
    environment:
      - OLLAMA_API_BASE_URL=http://ollama:11434/api
    depends_on:
      - ollama
    restart: unless-stopped

volumes:
  ollama_data:
"""
        
        return compose


# Singleton instance
_ollama_assistant = None


def get_ollama_assistant() -> OllamaAssistant:
    """Get singleton instance of Ollama assistant."""
    global _ollama_assistant
    if _ollama_assistant is None:
        _ollama_assistant = OllamaAssistant()
    return _ollama_assistant