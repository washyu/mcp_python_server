"""
Unit tests for ProxmoxAPIClient.
"""

import pytest
from unittest.mock import patch, AsyncMock
from src.utils.proxmox_api import ProxmoxAPIClient, ProxmoxNode


class TestProxmoxAPIClient:
    """Test ProxmoxAPIClient class."""
    
    @pytest.mark.unit
    def test_init_with_password(self):
        """Test initialization with password auth."""
        client = ProxmoxAPIClient(
            host="192.168.10.200",
            username="root@pam",
            password="test_password",
            verify_ssl=False
        )
        
        assert client.host == "https://192.168.10.200"
        assert client.username == "root@pam"
        assert client.password == "test_password"
        assert client.use_token_auth is False
        assert client.ticket is None
    
    @pytest.mark.unit
    def test_init_with_token(self):
        """Test initialization with API token."""
        token = "root@pam!test=1234-5678"
        client = ProxmoxAPIClient(
            host="192.168.10.200",
            api_token=token,
            verify_ssl=False
        )
        
        assert client.host == "https://192.168.10.200"
        assert client.api_token == token
        assert client.use_token_auth is True
        assert client.ticket is None
    
    @pytest.mark.unit
    def test_host_normalization(self):
        """Test that host URLs are normalized correctly."""
        # Test with protocol
        client1 = ProxmoxAPIClient(host="https://192.168.10.200", api_token="test")
        assert client1.host == "https://192.168.10.200"
        
        # Test without protocol
        client2 = ProxmoxAPIClient(host="192.168.10.200", api_token="test")
        assert client2.host == "https://192.168.10.200"
        
        # Test with trailing slash
        client3 = ProxmoxAPIClient(host="https://192.168.10.200/", api_token="test")
        assert client3.host == "https://192.168.10.200"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticate_with_token(self):
        """Test authentication with API token (should return True immediately)."""
        client = ProxmoxAPIClient(
            host="192.168.10.200",
            api_token="root@pam!test=1234",
            verify_ssl=False
        )
        
        result = await client.authenticate()
        assert result is True
        assert client.ticket is None  # No ticket needed for token auth
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticate_with_password_success(self, mock_aiohttp_session, mock_proxmox_response):
        """Test successful password authentication."""
        session_mock, response_mock = mock_aiohttp_session
        response_mock.status = 200
        response_mock.json = AsyncMock(return_value=mock_proxmox_response["auth"])
        
        with patch("aiohttp.ClientSession", return_value=session_mock):
            client = ProxmoxAPIClient(
                host="192.168.10.200",
                username="root@pam",
                password="test_password",
                verify_ssl=False
            )
            
            result = await client.authenticate()
            
            assert result is True
            assert client.ticket == "PVE:root@pam:1234567890::ticket_value"
            assert client.csrf_token == "csrf_token_value"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticate_with_password_failure(self, mock_aiohttp_session):
        """Test failed password authentication."""
        session_mock, response_mock = mock_aiohttp_session
        response_mock.status = 401
        
        with patch("aiohttp.ClientSession", return_value=session_mock):
            client = ProxmoxAPIClient(
                host="192.168.10.200",
                username="root@pam",
                password="wrong_password",
                verify_ssl=False
            )
            
            result = await client.authenticate()
            
            assert result is False
            assert client.ticket is None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_nodes(self, mock_aiohttp_session, mock_proxmox_response):
        """Test listing nodes."""
        session_mock, response_mock = mock_aiohttp_session
        response_mock.status = 200
        response_mock.json = AsyncMock(return_value=mock_proxmox_response["nodes"])
        
        with patch("aiohttp.ClientSession", return_value=session_mock):
            client = ProxmoxAPIClient(
                host="192.168.10.200",
                api_token="root@pam!test=1234",
                verify_ssl=False
            )
            
            nodes = await client.list_nodes()
            
            assert len(nodes) == 1
            assert isinstance(nodes[0], ProxmoxNode)
            assert nodes[0].node == "proxmox"
            assert nodes[0].status == "online"
            assert nodes[0].cpu == 0.15
            assert nodes[0].maxcpu == 12
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_make_request_with_token(self, mock_aiohttp_session):
        """Test making requests with API token."""
        session_mock, response_mock = mock_aiohttp_session
        response_mock.status = 200
        response_mock.json = AsyncMock(return_value={"data": "test"})
        
        with patch("aiohttp.ClientSession", return_value=session_mock):
            client = ProxmoxAPIClient(
                host="192.168.10.200",
                api_token="root@pam!test=1234",
                verify_ssl=False
            )
            
            result = await client._make_request("GET", "/test")
            
            # Check Authorization header was set
            session_mock.request.assert_called_once()
            call_args = session_mock.request.call_args
            headers = call_args[1]["headers"]
            assert headers["Authorization"] == "PVEAPIToken=root@pam!test=1234"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_make_request_with_ticket(self, mock_aiohttp_session):
        """Test making requests with ticket auth."""
        session_mock, response_mock = mock_aiohttp_session
        response_mock.status = 200
        response_mock.json = AsyncMock(return_value={"data": "test"})
        
        with patch("aiohttp.ClientSession", return_value=session_mock):
            client = ProxmoxAPIClient(
                host="192.168.10.200",
                username="root@pam",
                password="test",
                verify_ssl=False
            )
            client.ticket = "test_ticket"
            client.csrf_token = "test_csrf"
            
            # Test GET request (no CSRF needed)
            await client._make_request("GET", "/test")
            call_args = session_mock.request.call_args
            headers = call_args[1]["headers"]
            assert headers["Cookie"] == "PVEAuthCookie=test_ticket"
            assert "CSRFPreventionToken" not in headers
            
            # Test POST request (CSRF needed)
            await client._make_request("POST", "/test", {"key": "value"})
            call_args = session_mock.request.call_args
            headers = call_args[1]["headers"]
            assert headers["Cookie"] == "PVEAuthCookie=test_ticket"
            assert headers["CSRFPreventionToken"] == "test_csrf"