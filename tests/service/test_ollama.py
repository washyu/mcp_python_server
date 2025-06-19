#!/usr/bin/env python3
"""
Quick test to check Ollama connectivity.
"""

import os
import sys
import pytest
import ollama
from rich.console import Console
from src.utils.config import Config

console = Console()

@pytest.mark.requires_ollama
def test_ollama():
    """Test Ollama connection with helpful output."""
    
    console.print("[bold]Testing Ollama Connection[/bold]\n")
    
    # Show configuration source
    console.print(f"Using configuration from .env file")
    console.print(f"Ollama Host: {Config.OLLAMA_HOST}")
    console.print(f"Default Model: {Config.OLLAMA_MODEL}")
    
    client = ollama.Client(**Config.get_ollama_client_params())
    
    try:
        # Try to list models
        console.print("\nConnecting to Ollama...", end="")
        models = client.list()
        console.print(" ✓ [green]Success![/green]")
        
        # Show available models
        model_list = models.get('models', [])
        if model_list:
            console.print(f"\nAvailable models ({len(model_list)}):")
            for model in model_list:
                size_gb = model.get('size', 0) / (1024**3)
                console.print(f"  • {model['model']} ({size_gb:.1f} GB)")
        else:
            console.print("\n[yellow]No models found. Pull a model with:[/yellow]")
            console.print("  ollama pull llama3.2:3b")
        
        return True
        
    except Exception as e:
        console.print(" ✗ [red]Failed![/red]")
        console.print(f"\nError: {e}")
        
        # Provide helpful suggestions
        console.print("\n[yellow]Troubleshooting tips:[/yellow]")
        
        if "connection refused" in str(e).lower():
            console.print("• Ollama doesn't appear to be running")
            
            # Check if we're in WSL
            if os.path.exists("/proc/sys/fs/binfmt_misc/WSLInterop"):
                console.print("\n[cyan]You're using WSL![/cyan]")
                console.print("If Ollama is running on Windows, you need to:")
                console.print("1. Configure Ollama to accept external connections")
                console.print("2. Set OLLAMA_HOST to your Windows IP:")
                console.print("   export OLLAMA_HOST=http://<windows-ip>:11434")
                console.print("\nSee WSL_SETUP.md for detailed instructions")
            else:
                console.print("• Start Ollama with: ollama serve")
        
        return False

if __name__ == "__main__":
    success = test_ollama()
    sys.exit(0 if success else 1)