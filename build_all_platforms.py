#!/usr/bin/env python3
"""
Cross-platform build script for creating executables for Windows, Linux, and macOS.
This script should be run on each platform to create native executables.
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path

def get_platform_name():
    """Get a standardized platform name for the build."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "darwin":
        return f"macos-{machine}"
    elif system == "linux":
        return f"linux-{machine}"
    elif system == "windows":
        return f"windows-{machine}"
    else:
        return f"{system}-{machine}"

def build_executable(platform_name=None):
    """Build the homelab-mcp-server executable for the current or specified platform."""
    
    # Ensure we're in the right directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Use current platform if not specified
    if platform_name is None:
        platform_name = get_platform_name()
    
    print(f"🏗️  Building for platform: {platform_name}")
    
    # Clean previous builds
    dist_dir = project_root / "dist" / platform_name
    build_dir = project_root / "build"
    spec_file = project_root / "homelab-mcp-server.spec"
    
    # Create platform-specific dist directory
    dist_dir.mkdir(parents=True, exist_ok=True)
    
    # Clean build artifacts
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if spec_file.exists():
        spec_file.unlink()
    
    # Base PyInstaller command
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "homelab-mcp-server",
        "--onefile",
        "--clean",
        "--noconfirm",
        "--console",
        "--distpath", str(dist_dir),  # Platform-specific output directory
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
        "--paths", "src",
        "--log-level", "INFO",
        "homelab_mcp_launcher.py"
    ]
    
    # Platform-specific options
    if platform.system() == "Darwin":
        pyinstaller_cmd.extend([
            "--osx-bundle-identifier", "com.homelab.mcp-server",
        ])
    elif platform.system() == "Windows":
        pyinstaller_cmd.extend([
            # Windows-specific options
            "--icon", "icon.ico" if Path("icon.ico").exists() else "NONE",
        ])
    
    print(f"📦 Building executable with PyInstaller...")
    print(f"Command: {' '.join(pyinstaller_cmd)}")
    
    try:
        # Run PyInstaller
        result = subprocess.run(pyinstaller_cmd, check=True)
        print(f"\n✅ Build successful for {platform_name}!")
        
        # Find the output file
        if platform.system() == "Windows":
            exe_name = "homelab-mcp-server.exe"
        else:
            exe_name = "homelab-mcp-server"
        
        exe_path = dist_dir / exe_name
        
        if exe_path.exists():
            # Make it executable on Unix-like systems
            if platform.system() != "Windows":
                exe_path.chmod(0o755)
            
            print(f"📦 Executable created: {exe_path}")
            print(f"📏 Size: {exe_path.stat().st_size / 1024 / 1024:.2f} MB")
            
            # Create a release info file
            info_file = dist_dir / "build_info.txt"
            with open(info_file, "w") as f:
                f.write(f"Platform: {platform_name}\n")
                f.write(f"Build Date: {platform.python_build()[1]}\n")
                f.write(f"Python Version: {sys.version}\n")
                f.write(f"File Size: {exe_path.stat().st_size} bytes\n")
            
            return str(exe_path)
        else:
            print(f"❌ Executable not found in expected location: {exe_path}")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

def create_release_archive():
    """Create a release archive with all platform executables."""
    project_root = Path(__file__).parent
    dist_dir = project_root / "dist"
    
    # Find all platform builds
    platforms = []
    for platform_dir in dist_dir.iterdir():
        if platform_dir.is_dir() and "-" in platform_dir.name:
            platforms.append(platform_dir.name)
    
    if not platforms:
        print("❌ No platform builds found!")
        return
    
    print(f"\n📦 Found builds for platforms: {', '.join(platforms)}")
    
    # Create release directory
    release_dir = project_root / "releases"
    release_dir.mkdir(exist_ok=True)
    
    # Copy executables to release directory with platform suffix
    for platform_name in platforms:
        platform_dir = dist_dir / platform_name
        
        # Find executable
        exe_files = list(platform_dir.glob("homelab-mcp-server*"))
        if exe_files:
            exe_file = exe_files[0]
            
            # Create new filename with platform
            if exe_file.suffix == ".exe":
                new_name = f"homelab-mcp-server-{platform_name}.exe"
            else:
                new_name = f"homelab-mcp-server-{platform_name}"
            
            # Copy to release directory
            dest_path = release_dir / new_name
            shutil.copy2(exe_file, dest_path)
            print(f"✅ Copied {platform_name} executable to {dest_path}")

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Build homelab-mcp-server executables")
    parser.add_argument("--platform", help="Target platform (default: current platform)")
    parser.add_argument("--all", action="store_true", help="Build for all platforms (requires appropriate environment)")
    parser.add_argument("--release", action="store_true", help="Create release archive from existing builds")
    
    args = parser.parse_args()
    
    if args.release:
        create_release_archive()
    elif args.all:
        # Note: Cross-compilation is limited, this would typically be done in CI/CD
        print("⚠️  Cross-compilation is limited. For best results, build on each target platform.")
        print("   Consider using GitHub Actions or other CI/CD for multi-platform builds.")
        build_executable()
    else:
        build_executable(args.platform)

if __name__ == "__main__":
    main()