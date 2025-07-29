#!/usr/bin/env python3
"""
Build script for creating a standalone executable using PyInstaller.
PyInstaller is typically faster than Nuitka for compilation.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def build_executable():
    """Build the homelab-mcp-server executable using PyInstaller."""
    
    # Ensure we're in the right directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Clean previous builds
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"
    spec_file = project_root / "homelab-mcp-server.spec"
    
    for path in [dist_dir, build_dir, spec_file]:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
    
    # PyInstaller command
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "homelab-mcp-server",
        "--onefile",  # Create a single executable file
        "--clean",  # Clean PyInstaller cache before building
        "--noconfirm",  # Replace output directory without confirmation
        "--console",  # Console application (not windowed)
        "--add-data", f"src/homelab_mcp/service_templates{os.pathsep}homelab_mcp/service_templates",
        "--hidden-import", "homelab_mcp",
        "--hidden-import", "mcp",
        "--hidden-import", "mcp.server",
        "--hidden-import", "asyncssh",
        "--hidden-import", "yaml",
        "--hidden-import", "jsonschema",
        "--hidden-import", "httpx",
        "--hidden-import", "aiofiles",
        "--hidden-import", "rich",
        "--hidden-import", "aiohttp",
        "--hidden-import", "multidict",
        "--hidden-import", "yarl",
        "--hidden-import", "attrs",
        "--hidden-import", "certifi",
        "--hidden-import", "charset_normalizer",
        "--paths", "src",  # Add src to Python path
        "--log-level", "INFO",
        "homelab_mcp_launcher.py"  # Entry point
    ]
    
    # Platform-specific options
    if sys.platform == "darwin":
        pyinstaller_cmd.extend([
            # Don't specify target-arch to build for native architecture only
            "--osx-bundle-identifier", "com.homelab.mcp-server",
        ])
    
    print("Building executable with PyInstaller...")
    print(f"Command: {' '.join(pyinstaller_cmd)}")
    
    try:
        # Run PyInstaller
        result = subprocess.run(pyinstaller_cmd, check=True)
        print("\n✅ Build successful!")
        
        # Find the output file
        if sys.platform == "win32":
            exe_path = dist_dir / "homelab-mcp-server.exe"
        else:
            exe_path = dist_dir / "homelab-mcp-server"
        
        if exe_path.exists():
            # Make it executable on Unix-like systems
            if sys.platform != "win32":
                exe_path.chmod(0o755)
            
            print(f"📦 Executable created: {exe_path}")
            print(f"📏 Size: {exe_path.stat().st_size / 1024 / 1024:.2f} MB")
            
            # Test the executable
            print("\n🧪 Testing executable...")
            test_cmd = [str(exe_path), "--version"]
            try:
                # Create a test by just running it briefly
                test_process = subprocess.Popen(
                    [str(exe_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE
                )
                # Send a simple initialize request
                test_input = '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}\n'
                stdout, stderr = test_process.communicate(input=test_input.encode(), timeout=5)
                
                if b'"protocolVersion"' in stdout:
                    print("✅ Executable test passed!")
                else:
                    print(f"⚠️  Executable test returned unexpected output: {stdout.decode()}")
                    if stderr:
                        print(f"   Stderr: {stderr.decode()}")
            except subprocess.TimeoutExpired:
                test_process.kill()
                print("✅ Executable started successfully (timeout expected for MCP server)")
            except Exception as e:
                print(f"⚠️  Executable test warning: {e}")
            
            # Create convenience symlink in project root
            symlink_path = project_root / "homelab-mcp-server"
            if symlink_path.exists():
                symlink_path.unlink()
            symlink_path.symlink_to(exe_path.relative_to(project_root))
            print(f"\n🔗 Created symlink: {symlink_path} -> {exe_path.relative_to(project_root)}")
            
            print("\n📝 Usage:")
            print(f"   ./homelab-mcp-server")
            print("\n   Or copy the executable from dist/ to anywhere in your PATH")
            
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