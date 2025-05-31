"""
Pytest configuration and fixtures.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def mock_config(monkeypatch):
    """Mock configuration values."""
    monkeypatch.setattr("config.Config.PROXMOX_HOST", "192.168.10.200")
    monkeypatch.setattr("config.Config.PROXMOX_USER", "root@pam")
    monkeypatch.setattr("config.Config.PROXMOX_PASSWORD", "test_password")
    monkeypatch.setattr("config.Config.PROXMOX_API_TOKEN", "")
    monkeypatch.setattr("config.Config.PROXMOX_VERIFY_SSL", False)


@pytest.fixture
def mock_proxmox_response():
    """Mock Proxmox API responses."""
    return {
        "auth": {
            "data": {
                "ticket": "PVE:root@pam:1234567890::ticket_value",
                "CSRFPreventionToken": "csrf_token_value"
            }
        },
        "nodes": {
            "data": [
                {
                    "node": "proxmox",
                    "status": "online",
                    "cpu": 0.15,
                    "maxcpu": 12,
                    "mem": 8589934592,
                    "maxmem": 17179869184,
                    "disk": 10737418240,
                    "maxdisk": 107374182400,
                    "uptime": 864000,
                    "level": "",
                    "id": "node/proxmox"
                }
            ]
        },
        "version": {
            "data": {
                "version": "8.2.4",
                "release": "8.2",
                "repoid": "1234abcd"
            }
        }
    }


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session."""
    # Create response mock that implements async context manager
    response = Mock()
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    
    # Create session mock
    session = Mock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    
    # Session methods return the response context manager
    session.post = Mock(return_value=response)
    session.get = Mock(return_value=response)
    session.request = Mock(return_value=response)
    
    return session, response


@pytest.fixture
def mock_credential_manager(temp_dir):
    """Mock credential manager with temp storage."""
    from src.utils.credential_manager import CredentialManager, EncryptedFileBackend
    
    backend = EncryptedFileBackend(
        storage_path=temp_dir / "test_credentials.enc",
        password="test_password"
    )
    return CredentialManager(backend)


@pytest.fixture
def mock_websocket():
    """Mock WebSocket for testing."""
    ws = AsyncMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock()
    ws.close = AsyncMock()
    ws.closed = False
    return ws