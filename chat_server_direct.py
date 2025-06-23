#!/usr/bin/env python3
"""Direct MCP integration without stdio subprocess."""

import asyncio
import json
from typing import AsyncIterator
from starlette.applications import Starlette
from starlette.responses import StreamingResponse, JSONResponse
from starlette.routing import Route
from starlette.middleware.cors import CORSMiddleware
import httpx


# Direct MCP tool implementation - no subprocess needed
def hello_world_tool() -> str:
    """Direct implementation of hello_world tool."""
    return "Hello from the Homelab MCP server"


class DirectChat:
    """Chat handler with direct MCP tool calls."""
    
    def __init__(self):
        import os
        self.ollama_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.model = "llama3"  # Will pull llama3 automatically
        
    async def chat(self, message: str) -> AsyncIterator[str]:
        """Process chat message."""
        tool_response = None
        
        # Check if message mentions hello - direct tool call
        if "hello" in message.lower() or "hi" in message.lower():
            try:
                print("Calling hello_world tool directly...")
                tool_response = hello_world_tool()
                print(f"MCP Tool Response: {tool_response}")
            except Exception as e:
                print(f"Error calling MCP tool: {e}")
        
        # Build prompt with tool response if available
        if tool_response:
            prompt = f"""User: {message}

You have access to an MCP server. When the user greets you, you called the hello_world tool and got this response: "{tool_response}"

Please mention this response in your reply to the user."""
        else:
            prompt = f"""User: {message}

You have access to an MCP server with a hello_world tool, but it wasn't needed for this message."""
        
        print(f"Sending to Ollama: {prompt[:100]}...")
        
        # Send to Ollama
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": True
                    },
                    timeout=60.0
                )
                
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                        except json.JSONDecodeError:
                            print(f"Failed to parse JSON: {line}")
            except httpx.ConnectError:
                yield "Error: Cannot connect to Ollama. Is it running on http://localhost:11434?"
            except Exception as e:
                yield f"Error communicating with Ollama: {str(e)}"


# Global chat instance
chat_handler = DirectChat()


async def health_check(request):
    """Health check endpoint."""
    return JSONResponse({"status": "healthy", "service": "direct-chat"})


async def list_tools(request):
    """List available MCP tools."""
    return JSONResponse({
        "tools": [{"name": "hello_world", "description": "Returns a greeting from the homelab MCP server"}]
    })


async def chat_endpoint(request):
    """Handle chat messages."""
    try:
        data = await request.json()
        message = data.get("message", "")
        
        print(f"Received message: {message}")
        
        async def generate():
            try:
                async for chunk in chat_handler.chat(message):
                    # Send as SSE format
                    yield f"data: {json.dumps({'response': chunk})}\\n\\n"
                yield f"data: {json.dumps({'done': True})}\\n\\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\\n\\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# Create Starlette app
app = Starlette(
    routes=[
        Route("/health", health_check),
        Route("/api/tools", list_tools),
        Route("/api/chat", chat_endpoint, methods=["POST"])
    ]
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)