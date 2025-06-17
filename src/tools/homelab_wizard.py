"""
Beginner-friendly homelab setup wizard with educational guidance.
Helps users understand options, make informed decisions, and learn industry practices.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class HomelabProfile:
    """User's homelab profile and preferences."""
    experience_level: str  # beginner, intermediate, advanced
    primary_goals: List[str] = field(default_factory=list)
    budget_range: str = "moderate"
    time_commitment: str = "weekends"
    learning_interests: List[str] = field(default_factory=list)
    current_hardware: List[Dict[str, Any]] = field(default_factory=list)
    preferred_technologies: List[str] = field(default_factory=list)


@dataclass
class ServiceRecommendation:
    """Service recommendation with educational context."""
    name: str
    category: str
    difficulty: str  # beginner, intermediate, advanced
    description: str
    why_useful: str
    industry_relevance: str
    prerequisites: List[str] = field(default_factory=list)
    learning_resources: List[str] = field(default_factory=list)
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)


class HomelabWizard:
    """Interactive wizard for homelab setup with educational guidance."""
    
    def __init__(self):
        self.profiles: Dict[str, HomelabProfile] = {}
        self.service_catalog = self._initialize_service_catalog()
        self.learning_paths = self._initialize_learning_paths()
        
    def _initialize_service_catalog(self) -> Dict[str, ServiceRecommendation]:
        """Initialize catalog of services with educational information."""
        return {
            "proxmox": ServiceRecommendation(
                name="Proxmox VE",
                category="Virtualization Platform",
                difficulty="intermediate",
                description="Enterprise-grade virtualization platform that runs VMs and containers",
                why_useful="Learn the same virtualization concepts used in data centers. Great foundation for understanding cloud infrastructure.",
                industry_relevance="Similar to VMware vSphere and Microsoft Hyper-V used in enterprises. Skills directly transferable to cloud platforms like AWS EC2.",
                prerequisites=["Basic networking knowledge", "Comfortable with web interfaces"],
                learning_resources=[
                    "Proxmox official documentation",
                    "Learn Linux TV YouTube channel",
                    "r/Proxmox community"
                ],
                pros=[
                    "Free and open source",
                    "Professional-grade features",
                    "Supports both VMs and containers",
                    "Built-in backup and clustering"
                ],
                cons=[
                    "Steeper learning curve than simple solutions",
                    "Requires dedicated hardware",
                    "More complex than Docker alone"
                ]
            ),
            "lxd": ServiceRecommendation(
                name="LXD/LXC Containers",
                category="Container Platform",
                difficulty="beginner",
                description="Lightweight container system - like VMs but much more efficient",
                why_useful="Perfect stepping stone between Docker and full VMs. Learn container concepts without Docker's complexity.",
                industry_relevance="Understanding containers is essential for modern DevOps. LXD teaches the same concepts as Kubernetes but simpler.",
                prerequisites=["Basic Linux command line"],
                learning_resources=[
                    "Linux Containers official site",
                    "Ubuntu LXD tutorials",
                    "LXD for beginners guides"
                ],
                pros=[
                    "Very lightweight on resources",
                    "Easy to learn basics",
                    "System containers feel like VMs",
                    "Great for Raspberry Pi"
                ],
                cons=[
                    "Less popular than Docker",
                    "Fewer pre-made images",
                    "Linux-only technology"
                ]
            ),
            "docker": ServiceRecommendation(
                name="Docker",
                category="Application Containers",
                difficulty="intermediate",
                description="Industry-standard application containerization platform",
                why_useful="Docker is everywhere in modern tech. Essential skill for developers and DevOps engineers.",
                industry_relevance="Used by almost every tech company. Understanding Docker is often a job requirement for modern roles.",
                prerequisites=["Linux basics", "Understanding of ports and networking"],
                learning_resources=[
                    "Docker official tutorials",
                    "Docker Hub for finding images",
                    "Portainer for visual management"
                ],
                pros=[
                    "Industry standard",
                    "Huge ecosystem",
                    "Pre-built images for everything",
                    "Great for microservices"
                ],
                cons=[
                    "Can be complex for beginners",
                    "Security considerations",
                    "Resource overhead for GUI"
                ]
            ),
            "pihole": ServiceRecommendation(
                name="Pi-hole",
                category="Network Services",
                difficulty="beginner",
                description="Network-wide ad blocker and DNS server",
                why_useful="Immediately useful for your whole network. Great introduction to DNS and network services.",
                industry_relevance="Teaches DNS concepts used everywhere. Understanding DNS is fundamental for any IT role.",
                prerequisites=["Basic network setup"],
                learning_resources=[
                    "Pi-hole documentation",
                    "r/pihole community",
                    "YouTube setup guides"
                ],
                pros=[
                    "Immediate practical benefit",
                    "Easy to set up",
                    "Low resource usage",
                    "Great first project"
                ],
                cons=[
                    "Can break some sites/apps",
                    "Requires maintenance",
                    "Family might complain"
                ]
            ),
            "nextcloud": ServiceRecommendation(
                name="Nextcloud",
                category="Cloud Storage",
                difficulty="intermediate",
                description="Self-hosted cloud storage like Google Drive or Dropbox",
                why_useful="Take control of your data. Learn about web applications, databases, and storage systems.",
                industry_relevance="Similar architecture to enterprise content management systems. Good for understanding full-stack applications.",
                prerequisites=["Web server basics", "Understanding of storage"],
                learning_resources=[
                    "Nextcloud documentation",
                    "Nextcloud AIO (All-in-One)",
                    "Database basics tutorials"
                ],
                pros=[
                    "Full control of your data",
                    "Rich feature set",
                    "Mobile apps available",
                    "Extensible with apps"
                ],
                cons=[
                    "Requires significant storage",
                    "Needs regular maintenance",
                    "Can be slow on weak hardware"
                ]
            ),
            "homeassistant": ServiceRecommendation(
                name="Home Assistant",
                category="Home Automation",
                difficulty="beginner",
                description="Open source home automation platform",
                why_useful="Practical home automation while learning about IoT, APIs, and automation concepts.",
                industry_relevance="IoT and automation are growing fields. Concepts apply to industrial automation and smart city projects.",
                prerequisites=["Basic networking"],
                learning_resources=[
                    "Home Assistant documentation",
                    "HA Community forums",
                    "YouTube automation tutorials"
                ],
                pros=[
                    "No coding required to start",
                    "Huge device support",
                    "Very active community",
                    "Practical daily use"
                ],
                cons=[
                    "Can become addictive",
                    "Some integrations are complex",
                    "Requires compatible devices"
                ]
            ),
            "jellyfin": ServiceRecommendation(
                name="Jellyfin/Plex",
                category="Media Server",
                difficulty="beginner",
                description="Self-hosted media streaming server like Netflix",
                why_useful="Learn about media transcoding, streaming protocols, and server management with immediate family benefits.",
                industry_relevance="Understanding media delivery is valuable. Similar tech powers Netflix, YouTube, and corporate video platforms.",
                prerequisites=["Basic file management", "Understanding of media formats"],
                learning_resources=[
                    "Jellyfin documentation",
                    "r/jellyfin community",
                    "Transcoding guides"
                ],
                pros=[
                    "Family-friendly project",
                    "Immediate practical use",
                    "Good first server project",
                    "Teaches about media codecs"
                ],
                cons=[
                    "Can use significant CPU for transcoding",
                    "Requires media library",
                    "Network bandwidth considerations"
                ]
            )
        }
        
    def _initialize_learning_paths(self) -> Dict[str, List[str]]:
        """Initialize recommended learning paths."""
        return {
            "absolute_beginner": [
                "pihole",  # Start with network basics
                "jellyfin",  # Add media server
                "homeassistant",  # Try automation
                "docker",  # Learn containers
                "nextcloud"  # Full web application
            ],
            "developer_focused": [
                "docker",  # Start with containers
                "lxd",  # System containers
                "proxmox",  # Full virtualization
                "nextcloud",  # Complex web app
                "gitlab"  # CI/CD pipeline
            ],
            "network_focused": [
                "pihole",  # DNS basics
                "opnsense",  # Firewall/routing
                "nginx",  # Reverse proxy
                "wireguard",  # VPN
                "monitoring"  # Network monitoring
            ],
            "data_focused": [
                "nextcloud",  # File storage
                "postgresql",  # Databases
                "elasticsearch",  # Search/analytics
                "grafana",  # Visualization
                "backup"  # Backup solutions
            ]
        }
        
    async def start_interview(self, user_id: str) -> Dict[str, Any]:
        """Start the interactive interview process."""
        return {
            "message": "Welcome to your Homelab Journey! 🚀",
            "introduction": (
                "I'm here to help you build your own homelab - a personal IT environment where you can "
                "learn, experiment, and run useful services. Think of it as your own mini data center!\n\n"
                "A homelab is perfect for:\n"
                "• Learning skills used in real IT jobs\n"
                "• Running your own services (like your own Netflix or Google Drive)\n"
                "• Experimenting safely without breaking anything important\n"
                "• Building projects for your resume\n\n"
                "Let's start by understanding what you're hoping to achieve!"
            ),
            "first_question": {
                "id": "goals",
                "question": "What interests you most about having a homelab?",
                "options": [
                    "Learning IT/DevOps skills for my career",
                    "Self-hosting services to control my data",
                    "Home automation and smart home projects",
                    "Media server for movies/music/photos",
                    "Development and testing environment",
                    "Just curious and want to explore"
                ],
                "allows_multiple": True,
                "educational_note": "There's no wrong answer! Most homelabs evolve to serve multiple purposes."
            }
        }
        
    async def process_answer(
        self,
        user_id: str,
        question_id: str,
        answer: Any
    ) -> Dict[str, Any]:
        """Process user's answer and provide next question or recommendation."""
        
        # Initialize profile if needed
        if user_id not in self.profiles:
            self.profiles[user_id] = HomelabProfile(experience_level="beginner")
            
        profile = self.profiles[user_id]
        
        # Process based on question ID
        if question_id == "goals":
            profile.primary_goals = answer if isinstance(answer, list) else [answer]
            
            return {
                "feedback": self._get_goal_feedback(profile.primary_goals),
                "next_question": {
                    "id": "experience",
                    "question": "How would you describe your current technical experience?",
                    "options": [
                        "Complete beginner - I can use a computer but that's about it",
                        "Some experience - I've used command line and maybe installed Linux",
                        "Intermediate - I'm comfortable with Linux and basic networking",
                        "Advanced - I work in IT or have significant experience"
                    ],
                    "educational_note": (
                        "Don't worry if you're a beginner! Everyone starts somewhere, and "
                        "homelabs are perfect for learning at your own pace."
                    )
                }
            }
            
        elif question_id == "experience":
            profile.experience_level = self._map_experience_level(answer)
            
            return {
                "feedback": self._get_experience_feedback(profile.experience_level),
                "next_question": {
                    "id": "hardware",
                    "question": "What hardware do you have available? (Select all that apply)",
                    "options": [
                        "Raspberry Pi (any model)",
                        "Old laptop or desktop PC",
                        "Dedicated server or workstation",
                        "Just my main computer",
                        "Planning to buy hardware",
                        "Using cloud VPS/services"
                    ],
                    "allows_multiple": True,
                    "educational_note": (
                        "You can start with almost any hardware! Even a Raspberry Pi or "
                        "old laptop can run many useful services."
                    )
                }
            }
            
        elif question_id == "hardware":
            hardware_list = answer if isinstance(answer, list) else [answer]
            profile.current_hardware = [{"type": h, "suitable_for": self._get_hardware_capabilities(h)} 
                                       for h in hardware_list]
            
            return {
                "feedback": self._get_hardware_feedback(hardware_list),
                "next_question": {
                    "id": "time_commitment",
                    "question": "How much time can you dedicate to your homelab?",
                    "options": [
                        "Just a few hours on weekends",
                        "An hour or two most evenings",
                        "It's going to be my main hobby",
                        "Just want something that runs itself"
                    ],
                    "educational_note": (
                        "Be realistic! It's better to start small and grow than to "
                        "burn out on an overly ambitious project."
                    )
                }
            }
            
        elif question_id == "time_commitment":
            profile.time_commitment = answer
            
            # Generate personalized recommendations
            recommendations = await self._generate_recommendations(profile)
            
            return {
                "interview_complete": True,
                "summary": self._generate_profile_summary(profile),
                "recommendations": recommendations,
                "learning_path": self._suggest_learning_path(profile),
                "next_steps": self._generate_next_steps(profile)
            }
            
        return {"error": "Unknown question ID"}
        
    def _get_goal_feedback(self, goals: List[str]) -> str:
        """Provide encouraging feedback based on selected goals."""
        if "Learning IT/DevOps skills for my career" in goals:
            return (
                "Excellent choice! Homelab experience is highly valued by employers. "
                "You'll learn the same tools and concepts used in real data centers and cloud platforms."
            )
        elif "Self-hosting services to control my data" in goals:
            return (
                "Data sovereignty is increasingly important! You'll learn valuable skills while "
                "taking control of your digital life."
            )
        else:
            return (
                "Great goals! A homelab is perfect for exploring these interests while "
                "building practical skills."
            )
            
    def _get_experience_feedback(self, level: str) -> str:
        """Provide feedback based on experience level."""
        feedback = {
            "beginner": (
                "Perfect! Homelabs are an excellent way to learn. We'll start with "
                "user-friendly projects that teach fundamental concepts."
            ),
            "intermediate": (
                "Great foundation! You're ready for some interesting projects that will "
                "expand your skills into new areas."
            ),
            "advanced": (
                "Excellent! We can explore enterprise-grade solutions and complex "
                "architectures that will challenge and interest you."
            )
        }
        return feedback.get(level, "Let's find projects that match your skill level!")
        
    def _get_hardware_feedback(self, hardware: List[str]) -> str:
        """Provide feedback about hardware choices."""
        if "Raspberry Pi" in hardware:
            return (
                "Raspberry Pi is perfect for starting out! It's energy-efficient and "
                "surprisingly capable. Many people run entire homelabs on Pi clusters."
            )
        elif "Old laptop or desktop PC" in hardware:
            return (
                "Repurposing old hardware is the homelab way! That old laptop probably "
                "has more power than you think, perfect for learning."
            )
        elif "Dedicated server or workstation" in hardware:
            return (
                "Wow, serious hardware! You'll be able to run enterprise-grade software "
                "and really dive deep into virtualization and clustering."
            )
        else:
            return "We'll find solutions that work with your available resources!"
            
    def _map_experience_level(self, answer: str) -> str:
        """Map answer to experience level."""
        if "Complete beginner" in answer:
            return "beginner"
        elif "Advanced" in answer:
            return "advanced"
        else:
            return "intermediate"
            
    def _get_hardware_capabilities(self, hardware_type: str) -> List[str]:
        """Determine what services can run on given hardware."""
        capabilities = {
            "Raspberry Pi": ["pihole", "homeassistant", "lightweight_services"],
            "Old laptop or desktop PC": ["virtualization", "docker", "media_server", "storage"],
            "Dedicated server or workstation": ["proxmox", "kubernetes", "heavy_workloads"],
            "Just my main computer": ["docker_desktop", "light_vms", "development"],
            "Planning to buy hardware": ["anything_with_right_specs"],
            "Using cloud VPS/services": ["public_services", "learning_platform"]
        }
        return capabilities.get(hardware_type, ["basic_services"])
        
    async def _generate_recommendations(self, profile: HomelabProfile) -> List[Dict[str, Any]]:
        """Generate personalized service recommendations."""
        recommendations = []
        
        # Start with beginner-friendly options
        if profile.experience_level == "beginner":
            if any("Pi" in h["type"] for h in profile.current_hardware):
                recommendations.append({
                    "service": self.service_catalog["pihole"],
                    "reason": "Perfect first project for Raspberry Pi. Immediately useful and teaches networking basics.",
                    "difficulty": "Easy weekend project",
                    "time_estimate": "2-3 hours to set up"
                })
                
        # Add based on goals
        if "Media server" in profile.primary_goals:
            recommendations.append({
                "service": self.service_catalog["jellyfin"],
                "reason": "Stream your media collection anywhere. Family-friendly project that everyone will appreciate.",
                "difficulty": "Beginner friendly",
                "time_estimate": "1-2 hours basic setup"
            })
            
        if "Learning IT/DevOps" in profile.primary_goals:
            if profile.experience_level != "beginner":
                recommendations.append({
                    "service": self.service_catalog["docker"],
                    "reason": "Essential skill for modern DevOps. Every job posting mentions containers!",
                    "difficulty": "Intermediate",
                    "time_estimate": "Weekend to learn basics"
                })
                
        return recommendations[:3]  # Limit to top 3 to avoid overwhelming
        
    def _suggest_learning_path(self, profile: HomelabProfile) -> Dict[str, Any]:
        """Suggest a learning path based on profile."""
        if "Learning IT/DevOps" in profile.primary_goals:
            path_key = "developer_focused"
        elif profile.experience_level == "beginner":
            path_key = "absolute_beginner"
        else:
            path_key = "network_focused"
            
        path = self.learning_paths[path_key]
        
        return {
            "path_name": path_key.replace("_", " ").title(),
            "description": self._get_path_description(path_key),
            "stages": [
                {
                    "order": i + 1,
                    "service": service,
                    "why": self._get_stage_reasoning(service, i)
                }
                for i, service in enumerate(path[:4])  # First 4 stages
            ],
            "timeline": "3-6 months for solid foundation"
        }
        
    def _get_path_description(self, path_key: str) -> str:
        """Get description for learning path."""
        descriptions = {
            "absolute_beginner": "A gentle introduction that builds confidence with practical projects",
            "developer_focused": "Fast track to modern DevOps and development practices",
            "network_focused": "Deep dive into networking and security fundamentals",
            "data_focused": "Master data storage, processing, and visualization"
        }
        return descriptions.get(path_key, "Custom path for your interests")
        
    def _get_stage_reasoning(self, service: str, stage: int) -> str:
        """Explain why this service at this stage."""
        if stage == 0:
            return "Start here to build confidence with an easy win"
        elif stage == 1:
            return "Build on your success with another practical project"
        elif stage == 2:
            return "Ready for more complex concepts"
        else:
            return "Integrate your knowledge with advanced features"
            
    def _generate_profile_summary(self, profile: HomelabProfile) -> str:
        """Generate a summary of the user's profile."""
        hardware_summary = ", ".join([h["type"] for h in profile.current_hardware])
        
        return (
            f"Based on your {profile.experience_level} experience level and interest in "
            f"{', '.join(profile.primary_goals[:2])}, I've created a personalized homelab roadmap. "
            f"Your {hardware_summary} is perfect for getting started!"
        )
        
    def _generate_next_steps(self, profile: HomelabProfile) -> List[Dict[str, str]]:
        """Generate actionable next steps."""
        steps = []
        
        if profile.experience_level == "beginner":
            steps.append({
                "action": "Set up your first service",
                "details": "Pick one recommended service and follow a tutorial. Don't worry about doing it perfectly!",
                "time": "This weekend"
            })
            
        steps.append({
            "action": "Join the community",
            "details": "Subscribe to r/homelab and r/selfhosted on Reddit. Great places for help and inspiration!",
            "time": "Today"
        })
        
        steps.append({
            "action": "Document your journey",
            "details": "Start a simple blog or notes about what you learn. Great for your resume!",
            "time": "As you go"
        })
        
        return steps
        
    async def explain_concept(self, concept: str) -> Dict[str, Any]:
        """Explain technical concepts in beginner-friendly terms."""
        explanations = {
            "virtualization": {
                "simple": "Running multiple computers inside one physical computer, like having several phones in one!",
                "detailed": "Virtualization lets you create virtual machines (VMs) that act like separate computers but share the same hardware. Used everywhere from laptops to massive data centers.",
                "analogy": "Like having multiple apartments in one building - each is separate but shares the foundation.",
                "why_useful": "Test things safely, run multiple operating systems, make better use of hardware",
                "industry_relevance": "Foundation of cloud computing (AWS, Azure, Google Cloud)"
            },
            "containers": {
                "simple": "Lightweight boxes that hold applications and everything they need to run",
                "detailed": "Containers package applications with their dependencies, making them portable and consistent across different systems.",
                "analogy": "Like shipping containers - same container works on any ship, train, or truck",
                "why_useful": "Apps run the same everywhere, easy to deploy and scale, efficient resource use",
                "industry_relevance": "Docker and Kubernetes are industry standards for modern applications"
            },
            "reverse_proxy": {
                "simple": "A traffic director for your web services",
                "detailed": "Routes incoming web requests to different services based on the domain name or path",
                "analogy": "Like a receptionist directing visitors to the right office in a building",
                "why_useful": "Run multiple services on one IP address, add SSL certificates, improve security",
                "industry_relevance": "Used by every major website to handle traffic and security"
            }
        }
        
        return explanations.get(concept, {
            "simple": f"I'll explain {concept} in simple terms...",
            "detailed": f"Let me break down {concept} for you..."
        })
        
    async def compare_options(
        self,
        option1: str,
        option2: str,
        context: str = "general"
    ) -> Dict[str, Any]:
        """Compare two technology options with pros/cons."""
        
        # Example comparison
        if sorted([option1.lower(), option2.lower()]) == ["docker", "lxd"]:
            return {
                "comparison": "Docker vs LXD",
                "summary": "Both are container technologies but serve different purposes",
                "docker": {
                    "best_for": "Running applications in isolation",
                    "pros": ["Industry standard", "Huge ecosystem", "Pre-built images"],
                    "cons": ["Steeper learning curve", "Not full OS containers"],
                    "use_when": "You want to run specific applications or microservices"
                },
                "lxd": {
                    "best_for": "Running full Linux systems in containers",
                    "pros": ["Simpler than VMs", "Very lightweight", "Full OS experience"],
                    "cons": ["Less popular", "Fewer pre-made images", "Linux only"],
                    "use_when": "You want VM-like systems with container efficiency"
                },
                "recommendation": "Start with LXD if you're learning Linux administration, Docker if focused on application deployment",
                "can_use_both": "Yes! Many homelabs use LXD for infrastructure and Docker for applications"
            }
            
        return {
            "message": f"Comparing {option1} vs {option2}",
            "needs_specific": "Please let me know what specific aspects you'd like to compare"
        }


# Singleton instance
_homelab_wizard = None


def get_homelab_wizard() -> HomelabWizard:
    """Get singleton instance of homelab wizard."""
    global _homelab_wizard
    if _homelab_wizard is None:
        _homelab_wizard = HomelabWizard()
    return _homelab_wizard