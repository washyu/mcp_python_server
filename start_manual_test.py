#!/usr/bin/env python3
"""
Start services for manual testing with web UI chat client.
"""

import asyncio
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
import subprocess
import os

console = Console()

async def main():
    """Start services for manual testing."""
    console.print(Panel.fit("🧪 Manual Testing Setup", style="bold blue"))
    
    # Check what services to start
    use_mock = Confirm.ask("Use mock Proxmox API?", default=True)
    transport = Prompt.ask("Transport mode", choices=["websocket", "stdio"], default="websocket")
    
    console.print("\n📋 Starting services...\n")
    
    # Start mock API if requested
    if use_mock:
        console.print("🐳 Starting mock Proxmox API...")
        try:
            subprocess.run(
                ["docker-compose", "up", "-d"],
                cwd="../testing/mock-api",
                check=True,
                capture_output=True
            )
            console.print("✅ Mock API started at http://localhost:8080")
            os.environ["PROXMOX_HOST"] = "localhost:8080"
        except Exception as e:
            console.print(f"⚠️  Mock API failed to start: {e}")
    
    # Display connection info
    console.print("\n📡 Service Configuration:")
    console.print(f"  • MCP Transport: {transport}")
    console.print(f"  • Proxmox API: {'Mock (localhost:8080)' if use_mock else 'Real (192.168.10.200)'}")
    console.print(f"  • Ollama: {os.getenv('OLLAMA_HOST', 'http://192.168.10.185:11434')}")
    
    # Start MCP server
    console.print(f"\n🚀 Starting MCP server in {transport} mode...")
    console.print("\n" + "="*60)
    console.print("Server starting... Connect your web UI chat client to:")
    if transport == "websocket":
        console.print("  ws://localhost:8765", style="bold green")
    else:
        console.print("  Use stdio transport with your client", style="bold green")
    console.print("="*60 + "\n")
    
    # Run the server
    cmd = [sys.executable, "main.py", "--transport", transport]
    if os.getenv("DEBUG") == "true":
        cmd.append("--debug")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n\n⏹️  Shutting down...")
        
        if use_mock:
            console.print("🐳 Stopping mock API...")
            subprocess.run(
                ["docker-compose", "down"],
                cwd="../testing/mock-api",
                capture_output=True
            )
        
        console.print("✅ All services stopped")

if __name__ == "__main__":
    asyncio.run(main())