#!/usr/bin/env python3
"""
Health check utility for the Homelab MCP system.
Used by VS Code tasks to verify system readiness.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import aiohttp
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


class HealthChecker:
    """Check health of various system components."""
    
    def __init__(self):
        self.checks = []
        self.results = {}
        
    async def check_ollama(self) -> Tuple[bool, str]:
        """Check if Ollama is running and accessible."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:11434/api/tags") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m["name"] for m in data.get("models", [])]
                        if models:
                            return True, f"Running with {len(models)} models"
                        else:
                            return False, "Running but no models installed"
                    else:
                        return False, f"API returned status {resp.status}"
        except aiohttp.ClientConnectorError:
            return False, "Not running (connection refused)"
        except Exception as e:
            return False, f"Error: {str(e)}"
            
    async def check_mcp_server(self) -> Tuple[bool, str]:
        """Check if MCP WebSocket server is running."""
        try:
            import websockets
            async with websockets.connect("ws://localhost:8765") as ws:
                # Send a simple ping
                await ws.send('{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}')
                response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                return True, "WebSocket server responding"
        except ConnectionRefusedError:
            return False, "Not running (connection refused)"
        except Exception as e:
            return False, f"Error: {str(e)}"
            
    async def check_dependencies(self) -> Tuple[bool, str]:
        """Check if all Python dependencies are installed."""
        missing = []
        try:
            import mcp
        except ImportError:
            missing.append("mcp")
            
        try:
            import ollama
        except ImportError:
            missing.append("ollama")
            
        try:
            import aiohttp
        except ImportError:
            missing.append("aiohttp")
            
        try:
            import asyncssh
        except ImportError:
            missing.append("asyncssh")
            
        if missing:
            return False, f"Missing: {', '.join(missing)}"
        else:
            return True, "All dependencies installed"
            
    async def check_env_file(self) -> Tuple[bool, str]:
        """Check if .env file exists and has required values."""
        env_path = Path(__file__).parent.parent.parent / ".env"
        if not env_path.exists():
            return False, ".env file not found"
            
        # Check for required keys
        required = ["OLLAMA_MODEL", "OLLAMA_HOST"]
        missing = []
        
        with open(env_path) as f:
            content = f.read()
            for key in required:
                if f"{key}=" not in content:
                    missing.append(key)
                    
        if missing:
            return False, f"Missing keys: {', '.join(missing)}"
        else:
            return True, "Configuration complete"
            
    async def run_all_checks(self) -> Dict[str, Tuple[bool, str]]:
        """Run all health checks."""
        results = {}
        
        # Define checks
        checks = [
            ("Python Dependencies", self.check_dependencies),
            ("Environment Config", self.check_env_file),
            ("Ollama Service", self.check_ollama),
            ("MCP WebSocket", self.check_mcp_server),
        ]
        
        # Run checks
        for name, check_func in checks:
            try:
                results[name] = await check_func()
            except Exception as e:
                results[name] = (False, f"Check failed: {e}")
                
        return results
        
    def display_results(self, results: Dict[str, Tuple[bool, str]]):
        """Display health check results in a nice table."""
        table = Table(title="System Health Check")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Details", style="dim")
        
        all_ok = True
        for component, (ok, details) in results.items():
            status = "✅ OK" if ok else "❌ FAIL"
            status_color = "green" if ok else "red"
            table.add_row(component, f"[{status_color}]{status}[/{status_color}]", details)
            if not ok:
                all_ok = False
                
        console.print(table)
        
        if all_ok:
            console.print("\n[bold green]✅ All systems ready![/bold green]")
        else:
            console.print("\n[bold yellow]⚠️  Some components need attention[/bold yellow]")
            console.print("\nTo fix:")
            
            if not results["Python Dependencies"][0]:
                console.print("  • Run: uv sync")
                
            if not results["Environment Config"][0]:
                console.print("  • Copy .env.example to .env and configure")
                
            if not results["Ollama Service"][0]:
                console.print("  • Run: ollama serve")
                console.print("  • Install model: ollama pull deepseek-r1:8b")
                
        return all_ok


async def main():
    """Run health check and display results."""
    console.print(Panel.fit(
        "[bold cyan]🏥 Homelab MCP System Health Check[/bold cyan]",
        title="Health Check"
    ))
    
    checker = HealthChecker()
    results = await checker.run_all_checks()
    all_ok = checker.display_results(results)
    
    # Exit with appropriate code for VS Code
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    asyncio.run(main())