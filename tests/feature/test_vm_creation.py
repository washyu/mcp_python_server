"""
Tests for VM creation tools and cloud-init integration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.tools.vm_creation import ProxmoxVMCreator, VMCreationRequest, create_vm_tool
from src.tools.cloud_init_templates import CloudInitTemplates, get_cloud_init_config


class TestCloudInitTemplates:
    """Test cloud-init template generation."""
    
    def test_generate_secure_password(self):
        """Test password generation."""
        password = CloudInitTemplates.generate_secure_password()
        assert len(password) == 20
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isdigit() for c in password)
    
    def test_base_vm_config(self):
        """Test base VM configuration generation."""
        config = CloudInitTemplates.base_vm_config("test-vm")
        
        assert "users" in config
        assert len(config["users"]) == 1
        
        user = config["users"][0]
        assert user["name"] == "ansible-admin"
        assert "sudo" in user["groups"]
        assert user["sudo"] == "ALL=(ALL) NOPASSWD:ALL"
        
        assert "packages" in config
        assert "qemu-guest-agent" in config["packages"]
        assert "openssh-server" in config["packages"]
        assert "python3" in config["packages"]
        
        assert "runcmd" in config
        commands = config["runcmd"]
        assert any("systemctl enable qemu-guest-agent" in cmd for cmd in commands)
        assert any("systemctl start qemu-guest-agent" in cmd for cmd in commands)
    
    def test_get_cloud_init_config(self):
        """Test cloud-init config generation for different VM types."""
        # Test base configuration
        config_yaml = get_cloud_init_config("base", "test-vm")
        assert "#cloud-config" in config_yaml
        assert "users:" in config_yaml
        assert "ansible-admin" in config_yaml
        
        # Test development configuration
        dev_config = get_cloud_init_config("development", "dev-vm")
        assert "docker.io" in dev_config
        assert "nodejs" in dev_config
        
        # Test unknown type
        with pytest.raises(ValueError, match="Unknown VM type"):
            get_cloud_init_config("unknown", "test-vm")


class TestVMCreationRequest:
    """Test VM creation request dataclass."""
    
    def test_vm_creation_request_defaults(self):
        """Test default values for VM creation request."""
        request = VMCreationRequest(name="test-vm")
        
        assert request.name == "test-vm"
        assert request.cores == 2
        assert request.memory_mb == 4096
        assert request.disk_gb == 20
        assert request.template_id == 9000
        assert request.node is None
        assert request.username == "ansible-admin"
        assert request.install_qemu_agent is True
        assert request.install_docker is False
    
    def test_vm_creation_request_custom(self):
        """Test custom values for VM creation request."""
        request = VMCreationRequest(
            name="custom-vm",
            cores=4,
            memory_mb=8192,
            disk_gb=50,
            node="proxmox-2",
            install_docker=True
        )
        
        assert request.name == "custom-vm"
        assert request.cores == 4
        assert request.memory_mb == 8192
        assert request.disk_gb == 50
        assert request.node == "proxmox-2"
        assert request.install_docker is True


class TestProxmoxVMCreator:
    """Test VM creation functionality."""
    
    @pytest.fixture
    def mock_proxmox_client(self):
        """Mock Proxmox client."""
        client = AsyncMock()
        client.authenticate.return_value = True
        return client
    
    @pytest.fixture
    def vm_creator(self, mock_proxmox_client):
        """VM creator with mock client."""
        return ProxmoxVMCreator(mock_proxmox_client)
    
    def test_cloud_init_config_generation(self, vm_creator):
        """Test cloud-init configuration generation."""
        request = VMCreationRequest(
            name="test-vm",
            cores=2,
            memory_mb=4096,
            install_docker=True
        )
        
        config = vm_creator.generate_cloud_init_config(request)
        
        assert "users:" in config
        assert "ansible-admin" in config
        assert "qemu-guest-agent" in config
        assert "docker.io" in config
        assert "systemctl enable qemu-guest-agent" in config
    
    @pytest.mark.asyncio
    async def test_get_next_vm_id_empty_cluster(self, vm_creator, mock_proxmox_client):
        """Test VM ID generation for empty cluster."""
        # Mock empty cluster
        mock_proxmox_client._make_request.side_effect = [
            {"data": [{"node": "proxmox"}]},  # nodes response
            {"data": []}  # empty VMs response
        ]
        
        vm_id = await vm_creator.get_next_vm_id()
        assert vm_id == 100
    
    @pytest.mark.asyncio
    async def test_get_next_vm_id_existing_vms(self, vm_creator, mock_proxmox_client):
        """Test VM ID generation with existing VMs."""
        # Mock cluster with existing VMs
        mock_proxmox_client._make_request.side_effect = [
            {"data": [{"node": "proxmox"}]},  # nodes response
            {"data": [
                {"vmid": "100"},
                {"vmid": "105"},
                {"vmid": "200"}
            ]}  # VMs response
        ]
        
        vm_id = await vm_creator.get_next_vm_id()
        assert vm_id == 201
    
    @pytest.mark.asyncio
    async def test_select_optimal_node_specified(self, vm_creator):
        """Test node selection when node is specified."""
        request = VMCreationRequest(name="test-vm", node="custom-node")
        
        node = await vm_creator.select_optimal_node(request)
        assert node == "custom-node"
    
    @pytest.mark.asyncio
    async def test_select_optimal_node_auto_select(self, vm_creator, mock_proxmox_client):
        """Test automatic node selection based on available memory."""
        request = VMCreationRequest(name="test-vm", memory_mb=4096)
        
        # Mock cluster resources
        mock_proxmox_client._make_request.return_value = {
            "data": [
                {
                    "type": "node",
                    "node": "node1",
                    "status": "online",
                    "maxmem": 16 * 1024**3,  # 16GB
                    "mem": 8 * 1024**3       # 8GB used
                },
                {
                    "type": "node", 
                    "node": "node2",
                    "status": "online",
                    "maxmem": 32 * 1024**3,  # 32GB
                    "mem": 4 * 1024**3       # 4GB used
                }
            ]
        }
        
        node = await vm_creator.select_optimal_node(request)
        assert node == "node2"  # Should select node with more available memory
    
    @pytest.mark.asyncio
    async def test_select_optimal_node_insufficient_memory(self, vm_creator, mock_proxmox_client):
        """Test node selection when no node has enough memory."""
        request = VMCreationRequest(name="test-vm", memory_mb=16384)  # 16GB
        
        # Mock cluster with insufficient resources
        mock_proxmox_client._make_request.return_value = {
            "data": [
                {
                    "type": "node",
                    "node": "node1", 
                    "status": "online",
                    "maxmem": 8 * 1024**3,   # 8GB total
                    "mem": 4 * 1024**3       # 4GB used, only 4GB available
                }
            ]
        }
        
        with pytest.raises(ValueError, match="No node has enough memory"):
            await vm_creator.select_optimal_node(request)


class TestVMCreationTool:
    """Test MCP tool interface for VM creation."""
    
    @pytest.mark.asyncio
    @patch('src.tools.vm_creation.ProxmoxVMCreator')
    async def test_create_vm_tool_success(self, mock_creator_class):
        """Test successful VM creation through MCP tool."""
        # Mock VM creator
        mock_creator = AsyncMock()
        mock_creator_class.return_value = mock_creator
        
        # Mock successful VM creation
        mock_result = MagicMock()
        mock_result.vm_id = 101
        mock_result.name = "test-vm"
        mock_result.node = "proxmox"
        mock_result.ip_address = "192.168.1.101"
        mock_result.ssh_user = "ansible-admin"
        mock_result.status = "running"
        mock_result.services = ["qemu-guest-agent", "docker"]
        
        mock_creator.create_vm.return_value = mock_result
        
        # Call the tool
        result = await create_vm_tool(
            name="test-vm",
            cores=4,
            memory_gb=8,
            install_docker=True
        )
        
        # Verify result
        assert result["success"] is True
        assert result["vm_id"] == 101
        assert result["name"] == "test-vm"
        assert result["node"] == "proxmox"
        assert result["ip_address"] == "192.168.1.101"
        assert "test-vm" in result["message"]
        assert "docker" in result["services"]
    
    @pytest.mark.asyncio
    @patch('src.tools.vm_creation.ProxmoxVMCreator')
    async def test_create_vm_tool_failure(self, mock_creator_class):
        """Test VM creation failure through MCP tool."""
        # Mock VM creator
        mock_creator = AsyncMock()
        mock_creator_class.return_value = mock_creator
        
        # Mock VM creation failure
        mock_creator.create_vm.side_effect = Exception("Insufficient resources")
        
        # Call the tool
        result = await create_vm_tool(name="test-vm")
        
        # Verify error result
        assert result["success"] is False
        assert "Insufficient resources" in result["error"]
        assert "Failed to create VM" in result["message"]
    
    @pytest.mark.asyncio
    @patch('src.tools.vm_creation.ProxmoxVMCreator')
    async def test_create_vm_tool_parameter_conversion(self, mock_creator_class):
        """Test parameter conversion in MCP tool."""
        # Mock VM creator
        mock_creator = AsyncMock()
        mock_creator_class.return_value = mock_creator
        
        # Mock successful creation
        mock_result = MagicMock()
        mock_result.vm_id = 102
        mock_result.name = "param-test"
        mock_result.node = "proxmox"
        mock_result.ip_address = None
        mock_result.ssh_user = "ansible-admin"
        mock_result.status = "created"
        mock_result.services = ["qemu-guest-agent"]
        
        mock_creator.create_vm.return_value = mock_result
        
        # Call with float memory value
        await create_vm_tool(
            name="param-test",
            memory_gb=4.5,  # Float value
            template_id=9000
        )
        
        # Verify the request was created with correct memory conversion
        mock_creator.create_vm.assert_called_once()
        request = mock_creator.create_vm.call_args[0][0]
        assert request.memory_mb == 4608  # 4.5 * 1024
        assert request.template_id == 9000