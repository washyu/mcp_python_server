#!/usr/bin/env python3
"""
Test the wizard functionality independently.
"""

import asyncio
from rich.console import Console
from rich.panel import Panel
from src.utils.setup_wizard import SetupWizard, WizardFlow, PROXMOX_WIZARD_FLOW

console = Console()


async def test_setup_wizard():
    """Test the full setup wizard."""
    console.print(Panel.fit(
        "[bold cyan]Testing Setup Wizard[/bold cyan]\n"
        "This will run through the configuration wizard.",
        title="Test Mode"
    ))
    
    wizard = SetupWizard(".env.test")
    
    # Run only Proxmox section for testing
    config = await wizard.run(["proxmox"])
    
    console.print("\n[bold green]Test completed![/bold green]")
    console.print(f"Configuration would be saved to: .env.test")
    
    return config


async def test_wizard_flow():
    """Test the wizard flow component."""
    console.print(Panel.fit(
        "[bold cyan]Testing Wizard Flow[/bold cyan]\n"
        "This tests the chat-based wizard flow.",
        title="Flow Test"
    ))
    
    flow = WizardFlow()
    flow.define_flow("test_proxmox", PROXMOX_WIZARD_FLOW)
    
    # Start the flow
    step = flow.start_flow("test_proxmox")
    
    # Simulate user interaction
    test_responses = {
        "proxmox_host": "192.168.10.200",
        "proxmox_user": "root@pam",
        "proxmox_password": "test123",
        "verify_ssl": "no"
    }
    
    while step['type'] != 'complete':
        # Display prompt
        console.print(f"\n[cyan]{step['prompt']}[/cyan]")
        if step.get('default'):
            console.print(f"[dim]Default: {step['default']}[/dim]")
        
        # Simulate user response
        response = test_responses.get(step['key'], step.get('default', ''))
        console.print(f"[green]Simulated response:[/green] {response if 'password' not in step['key'] else '***'}")
        
        # Process response
        is_complete, result = flow.process_response("test_proxmox", response)
        
        if result['type'] == 'error':
            console.print(f"[red]Error: {result['message']}[/red]")
            break
        elif result['type'] == 'complete':
            console.print("\n[bold green]Flow completed![/bold green]")
            console.print("\n[bold]Collected data:[/bold]")
            for key, value in result['data'].items():
                display_value = value if 'password' not in key else '***'
                console.print(f"  • {key}: {display_value}")
            break
        else:
            step = result


async def test_custom_wizard():
    """Test creating a custom wizard flow."""
    console.print(Panel.fit(
        "[bold cyan]Testing Custom Wizard[/bold cyan]\n"
        "Creating a custom VM setup wizard.",
        title="Custom Flow"
    ))
    
    flow = WizardFlow()
    
    # Define a custom flow
    vm_wizard_steps = [
        {
            "key": "vm_purpose",
            "prompt": "What will this VM be used for?",
            "options": ["web-server", "database", "development", "other"],
            "validator": lambda x: (True, "") if x in ["web-server", "database", "development", "other"] else (False, "Please select a valid option")
        },
        {
            "key": "vm_os",
            "prompt": "Which operating system?",
            "options": ["ubuntu-22.04", "debian-12", "centos-9", "rocky-9"],
            "default": "ubuntu-22.04"
        },
        {
            "key": "vm_resources",
            "prompt": "Select resource tier",
            "options": ["minimal (1CPU/2GB)", "standard (2CPU/4GB)", "performance (4CPU/8GB)"],
            "default": "standard (2CPU/4GB)"
        }
    ]
    
    flow.define_flow("vm_setup", vm_wizard_steps)
    
    # Run through the flow
    step = flow.start_flow("vm_setup")
    
    test_responses = {
        "vm_purpose": "web-server",
        "vm_os": "ubuntu-22.04",
        "vm_resources": "standard (2CPU/4GB)"
    }
    
    while step['type'] != 'complete':
        console.print(f"\n[cyan]{step['prompt']}[/cyan]")
        if step.get('options'):
            console.print(f"Options: {', '.join(step['options'])}")
        
        response = test_responses.get(step['key'], '')
        console.print(f"[green]Response:[/green] {response}")
        
        is_complete, result = flow.process_response("vm_setup", response)
        
        if result['type'] == 'complete':
            console.print("\n[bold green]VM Setup Complete![/bold green]")
            console.print("\n[bold]VM Configuration:[/bold]")
            for key, value in result['data'].items():
                console.print(f"  • {key}: {value}")
            break
        else:
            step = result


async def main():
    """Run all tests."""
    tests = [
        ("Setup Wizard Test", test_setup_wizard),
        ("Wizard Flow Test", test_wizard_flow),
        ("Custom Wizard Test", test_custom_wizard)
    ]
    
    for name, test_func in tests:
        console.print(f"\n{'='*60}")
        console.print(f"[bold]{name}[/bold]")
        console.print(f"{'='*60}")
        
        try:
            await test_func()
        except Exception as e:
            console.print(f"[red]Test failed: {e}[/red]")
        
        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()


if __name__ == "__main__":
    asyncio.run(main())