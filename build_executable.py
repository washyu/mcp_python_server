#!/usr/bin/env python3
"""
Build script for creating a standalone executable using Nuitka.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def build_executable():
    """Build the homelab-mcp-server executable using Nuitka."""
    
    # Ensure we're in the right directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Clean previous builds
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"
    
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    
    dist_dir.mkdir(exist_ok=True)
    
    # Nuitka compilation command
    nuitka_cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",  # Create a standalone executable
        "--onefile",     # Create a single file executable
        "--assume-yes-for-downloads",  # Auto-download dependencies
        "--follow-imports",  # Follow all imports
        "--include-package=homelab_mcp",  # Include our package
        "--include-package=mcp",  # Include MCP package
        "--include-package=asyncssh",  # Include AsyncSSH
        "--include-package=yaml",  # Include PyYAML
        "--include-package=jsonschema",  # Include jsonschema
        "--include-package=httpx",  # Include httpx
        "--include-package=aiofiles",  # Include aiofiles
        "--include-package=rich",  # Include rich
        "--include-package-data=homelab_mcp",  # Include all package data
        "--include-data-dir=src/homelab_mcp/service_templates=homelab_mcp/service_templates",  # Include service templates
        "--output-dir=dist",
        "--output-filename=homelab-mcp-server",
        "--company-name=Homelab",
        "--product-name=Homelab MCP Server",
        "--file-version=0.2.0",
        "--product-version=0.2.0",
        "--file-description=MCP server for homelab VM infrastructure management",
        "--copyright=© 2024 Homelab MCP Server",
        "--python-flag=no_site",  # Don't use system site-packages
        "--python-flag=isolated",  # Run in isolated mode
        "--enable-plugin=anti-bloat",  # Remove unnecessary imports
        "--show-progress",
        "--show-memory",
        "src/homelab_mcp/server.py"  # Entry point
    ]
    
    # Add platform-specific options
    if sys.platform == "darwin":
        nuitka_cmd.extend([
            "--macos-create-app-bundle",  # Create macOS app bundle
            "--macos-app-name=Homelab MCP Server",
        ])
    elif sys.platform == "win32":
        nuitka_cmd.extend([
            "--windows-icon-from-ico=icon.ico",  # Add icon if available
            "--windows-console-mode=attach",  # Attach to console if available
        ])
    
    print("Building executable with Nuitka...")
    print(f"Command: {' '.join(nuitka_cmd)}")
    
    try:
        result = subprocess.run(nuitka_cmd, check=True)
        print("\n✅ Build successful!")
        
        # Find the output file
        if sys.platform == "darwin":
            exe_path = dist_dir / "homelab-mcp-server.app"
        elif sys.platform == "win32":
            exe_path = dist_dir / "homelab-mcp-server.exe"
        else:
            exe_path = dist_dir / "homelab-mcp-server"
        
        if exe_path.exists():
            print(f"📦 Executable created: {exe_path}")
            print(f"📏 Size: {exe_path.stat().st_size / 1024 / 1024:.2f} MB")
            
            # Create a simple wrapper script for easier execution
            wrapper_path = project_root / "homelab-mcp-server"
            wrapper_content = f"""#!/bin/bash
# Wrapper script for homelab-mcp-server executable
exec "{exe_path.absolute()}" "$@"
"""
            wrapper_path.write_text(wrapper_content)
            wrapper_path.chmod(0o755)
            print(f"🚀 Created wrapper script: {wrapper_path}")
            
        else:
            print("❌ Executable not found in expected location")
            return 1
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(build_executable())