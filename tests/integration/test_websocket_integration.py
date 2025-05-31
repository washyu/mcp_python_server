"""
Integration tests for WebSocket server and agent.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from src.server.websocket_server import MCPWebSocketServer
from src.agents.websocket_agent import WebSocketAIAgent


class TestWebSocketIntegration:
    """Test WebSocket server and agent integration."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_server_startup_and_shutdown(self):
        """Test server can start and stop cleanly."""
        server = MCPWebSocketServer()
        
        # Start server (it should bind to port)
        server_task = asyncio.create_task(server.start(port=9999))
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        
        # Stop server
        await server.stop()
        
        # Wait for server task to complete
        try:
            await asyncio.wait_for(server_task, timeout=1.0)
        except asyncio.TimeoutError:
            server_task.cancel()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_agent_connection_to_server(self, mock_websocket):
        """Test agent can connect to WebSocket server."""
        agent = WebSocketAIAgent()
        
        # Mock websocket connection
        with patch('websockets.connect', return_value=mock_websocket):
            # Test connection
            await agent.connect("ws://localhost:8765")
            
            # Should be connected
            assert agent.websocket is not None
            assert not agent.websocket.closed
            
            # Clean disconnect
            await agent.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_message_exchange(self, mock_websocket):
        """Test message exchange between server and agent."""
        agent = WebSocketAIAgent()
        
        # Mock incoming message
        test_message = {"type": "chat", "content": "Hello"}
        mock_websocket.recv.return_value = json.dumps(test_message)
        
        with patch('websockets.connect', return_value=mock_websocket):
            await agent.connect("ws://localhost:8765")
            
            # Send a message
            await agent.send_message("test message")
            
            # Verify websocket.send was called
            mock_websocket.send.assert_called()
            
            await agent.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_wizard_flow_integration(self, mock_websocket):
        """Test wizard integration through WebSocket."""
        agent = WebSocketAIAgent()
        
        # Mock wizard responses
        wizard_responses = [
            json.dumps({"type": "wizard_start", "wizard": "proxmox_setup"}),
            json.dumps({"type": "wizard_data", "data": {"host": "192.168.10.200", "username": "root@pam"}}),
            json.dumps({"type": "wizard_complete"})
        ]
        
        mock_websocket.recv.side_effect = wizard_responses
        
        with patch('websockets.connect', return_value=mock_websocket):
            with patch.object(agent, '_handle_wizard_start') as mock_wizard:
                await agent.connect("ws://localhost:8765")
                
                # Simulate receiving wizard start
                await agent._handle_message(wizard_responses[0])
                
                # Verify wizard handler was called
                mock_wizard.assert_called_once()
                
                await agent.disconnect()