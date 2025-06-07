#!/usr/bin/env python3
"""
Test AI-powered deployment suggestion functionality.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
sys.path.append(str(Path(__file__).parent.parent))

from src.tools.proxmox_discovery import ProxmoxDiscoveryTools
from src.utils.proxmox_api import ProxmoxGPU, ProxmoxCPU, ProxmoxNodeHardware
from mcp.types import TextContent


@pytest.fixture
def mock_inventory():
    """Mock inventory data for testing."""
    return {
        "nodes": [
            Mock(
                node="proxmox",
                maxcpu=12,
                maxmem=64 * 1024**3,  # 64GB
                cpu=0.05,  # 5% usage
                mem=16 * 1024**3,  # 16GB used
                hardware=ProxmoxNodeHardware(
                    gpus=[
                        ProxmoxGPU(
                            pci_id="0000:03:00.0",
                            vendor="AMD",
                            device="Radeon Instinct MI50",
                            model="AMD Radeon Instinct MI50",
                            suitable_for=["ai_training", "compute", "rocm"]
                        )
                    ],
                    cpu_details=ProxmoxCPU(
                        model="AMD Ryzen 9 5950X",
                        cores=16,
                        threads=32,
                        frequency="3.4GHz",
                        features=["avx", "avx2", "aes"]
                    ),
                    storage_devices=[]
                )
            ),
            Mock(
                node="compute-node",
                maxcpu=8,
                maxmem=32 * 1024**3,  # 32GB
                cpu=0.80,  # 80% usage (overloaded)
                mem=28 * 1024**3,  # 28GB used
                hardware=ProxmoxNodeHardware(gpus=[], cpu_details=None, storage_devices=[])
            )
        ],
        "vms": []
    }


@pytest.fixture
def discovery_tools():
    """Create discovery tools instance with mocked dependencies."""
    tools = ProxmoxDiscoveryTools()
    tools.get_inventory = AsyncMock()
    return tools


class TestWorkloadProfiles:
    """Test workload profile definitions and matching."""
    
    @pytest.mark.asyncio
    async def test_ai_training_profile(self, discovery_tools, mock_inventory):
        """Test AI training workload profile requirements."""
        discovery_tools.get_inventory.return_value = mock_inventory
        
        result = await discovery_tools.suggest_deployment("ai_training")
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        
        content = result[0].text
        assert "ai_training" in content.lower()
        assert "gpu: required" in content.lower()
        assert "cpu: 4+ cores" in content.lower()
        assert "memory: 16+ gb" in content.lower()
    
    @pytest.mark.asyncio
    async def test_database_profile(self, discovery_tools, mock_inventory):
        """Test database workload profile requirements."""
        discovery_tools.get_inventory.return_value = mock_inventory
        
        result = await discovery_tools.suggest_deployment("database")
        
        content = result[0].text
        assert "database" in content.lower()
        assert "gpu: optional" in content.lower()
        assert "storage: nvme" in content.lower()
        assert "cpu: 4+ cores" in content.lower()
    
    @pytest.mark.asyncio
    async def test_web_server_profile(self, discovery_tools, mock_inventory):
        """Test web server workload profile requirements."""
        discovery_tools.get_inventory.return_value = mock_inventory
        
        result = await discovery_tools.suggest_deployment("web_server")
        
        content = result[0].text
        assert "web_server" in content.lower()
        assert "cpu: 2+ cores" in content.lower()
        assert "memory: 4+ gb" in content.lower()


class TestNodeScoring:
    """Test node scoring algorithm for deployment suggestions."""
    
    @pytest.mark.asyncio
    async def test_gpu_node_preferred_for_ai(self, discovery_tools, mock_inventory):
        """Test that GPU-enabled node is preferred for AI workloads."""
        discovery_tools.get_inventory.return_value = mock_inventory
        
        result = await discovery_tools.suggest_deployment("ai_training")
        content = result[0].text
        
        # Should recommend proxmox node (has GPU)
        assert "🥇 **proxmox**" in content
        assert "ai-capable gpu" in content.lower()
        assert "recommended" in content.lower()
    
    @pytest.mark.asyncio
    async def test_overloaded_node_penalized(self, discovery_tools, mock_inventory):
        """Test that overloaded nodes are penalized in scoring."""
        discovery_tools.get_inventory.return_value = mock_inventory
        
        result = await discovery_tools.suggest_deployment("web_server")
        content = result[0].text
        
        # compute-node should have warnings due to high utilization
        if "compute-node" in content:
            assert "high cpu utilization" in content.lower()
    
    @pytest.mark.asyncio
    async def test_sufficient_resources_bonus(self, discovery_tools, mock_inventory):
        """Test that nodes with sufficient resources get scoring bonus."""
        discovery_tools.get_inventory.return_value = mock_inventory
        
        result = await discovery_tools.suggest_deployment("general")
        content = result[0].text
        
        # proxmox should get points for sufficient resources
        assert "sufficient cpu" in content.lower()
        assert "sufficient memory" in content.lower()


class TestCustomRequirements:
    """Test custom requirement overrides."""
    
    @pytest.mark.asyncio
    async def test_custom_memory_requirement(self, discovery_tools, mock_inventory):
        """Test custom memory requirements override defaults."""
        discovery_tools.get_inventory.return_value = mock_inventory
        
        custom_requirements = {"min_memory_gb": 32}
        result = await discovery_tools.suggest_deployment("general", custom_requirements)
        
        content = result[0].text
        assert "memory: 32+ gb" in content.lower()
    
    @pytest.mark.asyncio
    async def test_custom_gpu_requirement(self, discovery_tools, mock_inventory):
        """Test custom GPU requirements."""
        discovery_tools.get_inventory.return_value = mock_inventory
        
        custom_requirements = {"requires_gpu": True}
        result = await discovery_tools.suggest_deployment("general", custom_requirements)
        
        content = result[0].text
        assert "gpu: required" in content.lower()


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_no_nodes_available(self, discovery_tools):
        """Test deployment suggestions when no nodes are available."""
        discovery_tools.get_inventory.return_value = {"nodes": [], "vms": []}
        
        result = await discovery_tools.suggest_deployment("ai_training")
        
        assert len(result) == 1
        content = result[0].text
        assert "no nodes available" in content.lower()
    
    @pytest.mark.asyncio
    async def test_unknown_workload_type(self, discovery_tools, mock_inventory):
        """Test handling of unknown workload types."""
        discovery_tools.get_inventory.return_value = mock_inventory
        
        result = await discovery_tools.suggest_deployment("unknown_workload")
        
        # Should fall back to general profile
        content = result[0].text
        assert "general" in content.lower()
    
    @pytest.mark.asyncio
    async def test_insufficient_resources_all_nodes(self, discovery_tools):
        """Test when no nodes meet requirements."""
        # Create inventory with insufficient resources
        insufficient_inventory = {
            "nodes": [
                Mock(
                    node="small-node",
                    maxcpu=2,  # Too small for AI
                    maxmem=4 * 1024**3,  # Too small for AI  
                    cpu=0.1,
                    mem=1 * 1024**3,
                    hardware=ProxmoxNodeHardware(gpus=[], cpu_details=None, storage_devices=[])
                )
            ],
            "vms": []
        }
        
        discovery_tools.get_inventory.return_value = insufficient_inventory
        
        result = await discovery_tools.suggest_deployment("ai_training")
        content = result[0].text
        
        assert "not suitable" in content.lower()
        assert "insufficient" in content.lower()


class TestRecommendationDisplay:
    """Test recommendation display formatting."""
    
    @pytest.mark.asyncio
    async def test_recommendation_ranking(self, discovery_tools, mock_inventory):
        """Test that recommendations are properly ranked."""
        discovery_tools.get_inventory.return_value = mock_inventory
        
        result = await discovery_tools.suggest_deployment("ai_training")
        content = result[0].text
        
        # Should show ranking emojis
        ranking_found = any(emoji in content for emoji in ["🥇", "🥈", "🥉"])
        assert ranking_found
    
    @pytest.mark.asyncio
    async def test_reason_display(self, discovery_tools, mock_inventory):
        """Test that reasons for recommendations are displayed."""
        discovery_tools.get_inventory.return_value = mock_inventory
        
        result = await discovery_tools.suggest_deployment("ai_training")
        content = result[0].text
        
        # Should show checkmarks for positive reasons
        assert "✅" in content
        
        # Should show specific reasons
        reasons_found = any(phrase in content.lower() for phrase in [
            "sufficient cpu", "sufficient memory", "gpu", "low.*utilization"
        ])
        assert reasons_found
    
    @pytest.mark.asyncio 
    async def test_warning_display(self, discovery_tools, mock_inventory):
        """Test that warnings are displayed for unsuitable nodes."""
        discovery_tools.get_inventory.return_value = mock_inventory
        
        result = await discovery_tools.suggest_deployment("ai_training")
        content = result[0].text
        
        # compute-node should have warnings  
        if "compute-node" in content:
            assert "⚠️" in content


class TestScoringAlgorithm:
    """Test the numerical scoring algorithm."""
    
    def test_scoring_calculation_logic(self):
        """Test scoring calculation for different scenarios."""
        # This would test the internal scoring logic
        # For now, we test through integration with suggest_deployment
        pass
    
    @pytest.mark.asyncio
    async def test_gpu_bonus_scoring(self, discovery_tools, mock_inventory):
        """Test that GPU presence gives significant scoring bonus for AI workloads."""
        discovery_tools.get_inventory.return_value = mock_inventory
        
        result = await discovery_tools.suggest_deployment("ai_training")
        content = result[0].text
        
        # GPU node should be top recommendation
        lines = content.split('\n')
        gpu_line = next((line for line in lines if "proxmox" in line and "🥇" in line), None)
        assert gpu_line is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])