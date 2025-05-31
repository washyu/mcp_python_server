#!/usr/bin/env python3
"""
Test hardware discovery functionality including GPU detection and classification.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.proxmox_api import (
    ProxmoxAPIClient, ProxmoxGPU, ProxmoxCPU, ProxmoxStorage, ProxmoxNodeHardware
)


@pytest.fixture
def mock_proxmox_client():
    """Create a mock Proxmox API client."""
    client = Mock(spec=ProxmoxAPIClient)
    client.host = "192.168.10.200"
    return client


@pytest.fixture
def sample_pci_data():
    """Sample PCI device data from Proxmox API."""
    return {
        'data': [
            {
                'id': '0000:03:00.0',
                'class': 'VGA compatible controller',
                'vendor': 'Advanced Micro Devices, Inc. [AMD/ATI]',
                'device': 'Radeon Instinct MI50',
                'subsystem_vendor': 'Advanced Micro Devices, Inc. [AMD/ATI]',
                'subsystem_device': 'Radeon Instinct MI50'
            },
            {
                'id': '0000:00:02.0', 
                'class': 'VGA compatible controller',
                'vendor': 'Intel Corporation',
                'device': 'UHD Graphics 630',
                'subsystem_vendor': 'Intel Corporation',
                'subsystem_device': 'UHD Graphics 630'
            },
            {
                'id': '0000:00:1f.3',
                'class': 'Audio device',
                'vendor': 'Intel Corporation',
                'device': 'Cannon Lake PCH cAVS',
                'subsystem_vendor': 'Intel Corporation'
            }
        ]
    }


@pytest.fixture
def sample_cpu_data():
    """Sample CPU info data from Proxmox API."""
    return {
        'data': {
            'cpuinfo': {
                'model': 'AMD Ryzen 9 5950X 16-Core Processor',
                'cores': 16,
                'cpus': 32,
                'mhz': 3400,
                'flags': 'fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ht syscall nx mmxext fxsr_opt pdpe1gb rdtscp lm constant_tsc rep_good nopl nonstop_tsc cpuid extd_apicid aperfmperf rapl pni pclmulqdq monitor ssse3 fma cx16 sse4_1 sse4_2 x2apic movbe popcnt aes xsave avx f16c rdrand lahf_lm cmp_legacy svm extapic cr8_legacy abm sse4a misalignsse 3dnowprefetch osvw ibs skinit wdt tce topoext perfctr_core perfctr_nb bpext perfctr_llc mwaitx cpb cat_l3 cdp_l3 hw_pstate ssbd mba ibrs ibpb stibp vmmcall fsgsbase bmi1 avx2 smep bmi2 cqm rdt_a rdseed adx smap clflushopt clwb sha_ni xsaveopt xsavec xgetbv1 xsaves cqm_llc cqm_occup_llc cqm_mbm_total cqm_mbm_local clzero irperf xsaveerptr rdpru wbnoinvd arat npt lbrv svm_lock nrip_save tsc_scale vmcb_clean flushbyasid decodeassists pausefilter pfthreshold avic v_vmsave_vmload vgif v_spec_ctrl umip rdpid overflow_recov succor smca sev sev_es'
            }
        }
    }


@pytest.fixture  
def sample_disk_data():
    """Sample disk data from Proxmox API."""
    return {
        'data': [
            {
                'devpath': '/dev/nvme0n1',
                'device': 'nvme0n1',
                'model': 'Samsung SSD 970 EVO Plus 1TB',
                'size': 1000204886016,
                'type': 'nvme'
            },
            {
                'devpath': '/dev/sda',
                'device': 'sda', 
                'model': 'Seagate Barracuda ST4000DM004',
                'size': 4000787030016,
                'type': 'sata'
            },
            {
                'devpath': '/dev/sdb',
                'device': 'sdb',
                'model': 'Kingston SSD A400 480GB',
                'size': 480103981056,
                'type': 'sata'
            }
        ]
    }


class TestProxmoxGPUClassification:
    """Test GPU detection and classification logic."""
    
    def test_gpu_classification_amd_mi50(self):
        """Test AMD MI50 GPU is classified as AI-capable."""
        client = ProxmoxAPIClient("test", "test", "test")
        
        capabilities = client._classify_gpu_capabilities(
            "Advanced Micro Devices, Inc. [AMD/ATI]",
            "Radeon Instinct MI50"
        )
        
        assert "ai_training" in capabilities
        assert "compute" in capabilities
        assert "opencl" in capabilities
        assert "rocm" in capabilities
    
    def test_gpu_classification_nvidia_tesla(self):
        """Test NVIDIA Tesla GPU is classified as AI-capable."""
        client = ProxmoxAPIClient("test", "test", "test")
        
        capabilities = client._classify_gpu_capabilities(
            "NVIDIA Corporation",
            "Tesla V100"
        )
        
        assert "ai_training" in capabilities
        assert "compute" in capabilities
        assert "cuda" in capabilities
    
    def test_gpu_classification_consumer_nvidia(self):
        """Test consumer NVIDIA GPU classification."""
        client = ProxmoxAPIClient("test", "test", "test")
        
        capabilities = client._classify_gpu_capabilities(
            "NVIDIA Corporation", 
            "GeForce RTX 4090"
        )
        
        assert "gaming" in capabilities
        assert "ai_training" in capabilities
        assert "cuda" in capabilities
    
    def test_gpu_classification_intel_integrated(self):
        """Test Intel integrated graphics classification."""
        client = ProxmoxAPIClient("test", "test", "test")
        
        capabilities = client._classify_gpu_capabilities(
            "Intel Corporation",
            "UHD Graphics 630"
        )
        
        assert "display" in capabilities
        assert "ai_training" not in capabilities


class TestHardwareDiscovery:
    """Test hardware discovery functionality."""
    
    @pytest.mark.asyncio
    async def test_discover_gpus(self, mock_proxmox_client, sample_pci_data):
        """Test GPU discovery from PCI data."""
        # Setup client with real methods
        client = ProxmoxAPIClient("test", "test", "test")
        client._make_request = AsyncMock(return_value=sample_pci_data)
        
        gpus = await client._discover_gpus("proxmox")
        
        assert len(gpus) == 2  # MI50 + Intel UHD
        
        # Check MI50 GPU
        mi50 = next((gpu for gpu in gpus if "MI50" in gpu.model), None)
        assert mi50 is not None
        assert mi50.vendor == "Advanced Micro Devices, Inc. [AMD/ATI]"
        assert "ai_training" in mi50.suitable_for
        assert "rocm" in mi50.suitable_for
        
        # Check Intel GPU
        intel_gpu = next((gpu for gpu in gpus if "Intel" in gpu.vendor), None)
        assert intel_gpu is not None
        assert "display" in intel_gpu.suitable_for
    
    @pytest.mark.asyncio
    async def test_discover_cpu_details(self, sample_cpu_data):
        """Test CPU details discovery."""
        client = ProxmoxAPIClient("test", "test", "test")
        client._make_request = AsyncMock(return_value=sample_cpu_data)
        
        cpu = await client._discover_cpu_details("proxmox")
        
        assert cpu is not None
        assert "AMD Ryzen 9 5950X" in cpu.model
        assert cpu.cores == 16
        assert cpu.threads == 32
        assert cpu.frequency == "3.4GHz"
        assert "avx" in cpu.features
        assert "avx2" in cpu.features
        assert "aes" in cpu.features
    
    @pytest.mark.asyncio
    async def test_discover_storage_devices(self, sample_disk_data):
        """Test storage device discovery and classification."""
        client = ProxmoxAPIClient("test", "test", "test")
        client._make_request = AsyncMock(return_value=sample_disk_data)
        
        storage = await client._discover_storage_devices("proxmox")
        
        assert len(storage) == 3
        
        # Check NVMe SSD
        nvme = next((s for s in storage if "nvme" in s.device), None)
        assert nvme is not None
        assert nvme.type == "NVMe SSD"
        assert "Samsung" in nvme.model
        assert "1.0TB" in nvme.size
        
        # Check HDD
        hdd = next((s for s in storage if "Seagate" in s.model), None)
        assert hdd is not None
        assert nvme.type == "NVMe SSD"  # Should be classified by device path
        
        # Check SATA SSD
        ssd = next((s for s in storage if "Kingston" in s.model), None)
        assert ssd is not None
    
    def test_storage_type_classification(self):
        """Test storage type classification logic."""
        client = ProxmoxAPIClient("test", "test", "test")
        
        # Test NVMe detection
        assert client._classify_storage_type("/dev/nvme0n1", "Samsung SSD") == "NVMe SSD"
        
        # Test SSD detection by model
        assert client._classify_storage_type("/dev/sda", "Kingston SSD A400") == "SATA SSD"
        
        # Test HDD detection
        assert client._classify_storage_type("/dev/sdb", "Seagate Barracuda") == "SATA HDD"
        
        # Test fallback
        assert client._classify_storage_type("/dev/sdc", "Unknown Model") == "SATA Drive"
    
    def test_format_storage_size(self):
        """Test storage size formatting."""
        client = ProxmoxAPIClient("test", "test", "test")
        
        assert client._format_storage_size(0) == "Unknown"
        assert client._format_storage_size(1024) == "1.0KB"
        assert client._format_storage_size(1024**3) == "1.0GB"
        assert client._format_storage_size(1000204886016) == "931.3GB"  # 1TB drive
    
    @pytest.mark.asyncio
    async def test_discover_node_hardware_integration(self, sample_pci_data, sample_cpu_data, sample_disk_data):
        """Test complete node hardware discovery integration."""
        client = ProxmoxAPIClient("test", "test", "test")
        
        # Mock all the API calls
        def mock_make_request(method, endpoint):
            if "hardware/pci" in endpoint:
                return AsyncMock(return_value=sample_pci_data)()
            elif "status" in endpoint:
                return AsyncMock(return_value=sample_cpu_data)()
            elif "disks/list" in endpoint:
                return AsyncMock(return_value=sample_disk_data)()
            else:
                return AsyncMock(return_value={'data': []})()
        
        client._make_request = mock_make_request
        
        hardware = await client.discover_node_hardware("proxmox")
        
        assert isinstance(hardware, ProxmoxNodeHardware)
        assert len(hardware.gpus) == 2
        assert hardware.cpu_details is not None
        assert len(hardware.storage_devices) == 3
        
        # Check MI50 is detected
        mi50 = next((gpu for gpu in hardware.gpus if "MI50" in gpu.model), None)
        assert mi50 is not None
        assert "ai_training" in mi50.suitable_for


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_hardware_discovery_api_error(self):
        """Test hardware discovery when API calls fail."""
        client = ProxmoxAPIClient("test", "test", "test")
        client._make_request = AsyncMock(side_effect=Exception("API Error"))
        
        # Should not raise exception, but return empty hardware
        hardware = await client.discover_node_hardware("proxmox")
        
        assert isinstance(hardware, ProxmoxNodeHardware)
        assert len(hardware.gpus) == 0
        assert hardware.cpu_details is None
        assert len(hardware.storage_devices) == 0
    
    @pytest.mark.asyncio
    async def test_gpu_discovery_no_gpus(self):
        """Test GPU discovery when no GPUs are present."""
        client = ProxmoxAPIClient("test", "test", "test")
        client._make_request = AsyncMock(return_value={'data': []})
        
        gpus = await client._discover_gpus("proxmox")
        
        assert len(gpus) == 0
    
    @pytest.mark.asyncio
    async def test_cpu_discovery_missing_data(self):
        """Test CPU discovery with missing/malformed data."""
        client = ProxmoxAPIClient("test", "test", "test")
        client._make_request = AsyncMock(return_value={'data': {}})
        
        cpu = await client._discover_cpu_details("proxmox")
        
        assert cpu is None
    
    def test_gpu_classification_unknown_vendor(self):
        """Test GPU classification for unknown vendor."""
        client = ProxmoxAPIClient("test", "test", "test")
        
        capabilities = client._classify_gpu_capabilities("Unknown Vendor", "Unknown Device")
        
        assert capabilities == ["display"]  # Default fallback


if __name__ == "__main__":
    pytest.main([__file__, "-v"])