#!/usr/bin/env python3
"""
Fast build script for creating a standalone executable using Nuitka.
This version uses faster compilation options.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def build_executable():
    """Build the homelab-mcp-server executable using Nuitka with fast options."""
    
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
    
    # Nuitka compilation command with faster options
    nuitka_cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",  # Create a standalone executable
        # Remove --onefile for faster compilation
        "--assume-yes-for-downloads",  # Auto-download dependencies
        "--follow-imports",  # Follow all imports
        "--include-package=homelab_mcp",  # Include our package
        "--include-package-data=homelab_mcp",  # Include package data
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
        "--disable-console",  # Disable console in final build
        "--jobs=4",  # Use multiple cores for compilation
        "--lto=no",  # Disable link-time optimization for faster build
        "--clang",  # Use clang for faster compilation on macOS
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
            "--windows-console-mode=attach",  # Attach to console if available
        ])
    
    print("Building executable with Nuitka (fast mode)...")
    print(f"Command: {' '.join(nuitka_cmd)}")
    
    try:
        result = subprocess.run(nuitka_cmd, check=True)
        print("\n✅ Build successful!")
        
        # Find the output directory
        if sys.platform == "darwin":
            exe_dir = dist_dir / "homelab-mcp-server.app"
            exe_path = exe_dir / "Contents" / "MacOS" / "homelab-mcp-server"
        elif sys.platform == "win32":
            exe_dir = dist_dir / "homelab-mcp-server.dist"
            exe_path = exe_dir / "homelab-mcp-server.exe"
        else:
            exe_dir = dist_dir / "homelab-mcp-server.dist"
            exe_path = exe_dir / "homelab-mcp-server"
        
        if exe_path.exists():
            print(f"📦 Executable created: {exe_path}")
            
            # Get directory size
            total_size = sum(f.stat().st_size for f in exe_dir.rglob('*') if f.is_file())
            print(f"📏 Total size: {total_size / 1024 / 1024:.2f} MB")
            
            # Create a simple wrapper script for easier execution
            wrapper_path = project_root / "homelab-mcp-server"
            wrapper_content = f"""#!/bin/bash
# Wrapper script for homelab-mcp-server executable
exec "{exe_path.absolute()}" "$@"
"""
            wrapper_path.write_text(wrapper_content)
            wrapper_path.chmod(0o755)
            print(f"🚀 Created wrapper script: {wrapper_path}")
            
            # Instructions for creating a single file
            print("\n📝 To create a single executable file later, run:")
            print(f"   python -m nuitka --onefile --output-dir=dist-onefile {' '.join(nuitka_cmd[4:])}")
            
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