#!/usr/bin/env python3
"""Debug script for integration test issues."""

import sys
import subprocess

def check_docker():
    """Check if Docker is available and working."""
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Docker CLI: {result.stdout.strip()}")
        else:
            print("❌ Docker CLI not available")
            return False
    except FileNotFoundError:
        print("❌ Docker CLI not found")
        return False
    
    try:
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Docker daemon is running")
        else:
            print("❌ Docker daemon not running")
            return False
    except Exception as e:
        print(f"❌ Docker daemon error: {e}")
        return False
    
    return True

def check_python_docker():
    """Check if Python Docker SDK is available."""
    try:
        import docker
        print(f"✅ Python docker module imported: version {docker.__version__}")
        
        if hasattr(docker, 'from_env'):
            print("✅ docker.from_env() available")
        else:
            print("❌ docker.from_env() not available")
            return False
            
        try:
            client = docker.from_env()
            print("✅ Docker client created successfully")
            client.ping()
            print("✅ Docker client can ping daemon")
        except Exception as e:
            print(f"❌ Docker client error: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Cannot import docker module: {e}")
        return False
    
    return True

def check_port_2222():
    """Check if port 2222 is available."""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 2222))
        sock.close()
        if result == 0:
            print("⚠️  Port 2222 is in use (this might cause test conflicts)")
        else:
            print("✅ Port 2222 is available")
    except Exception as e:
        print(f"❌ Error checking port 2222: {e}")

def main():
    """Run all checks."""
    print("🔍 Debugging integration test environment...\n")
    
    print("1. Checking Docker CLI and daemon:")
    docker_ok = check_docker()
    print()
    
    print("2. Checking Python Docker SDK:")
    python_docker_ok = check_python_docker()
    print()
    
    print("3. Checking port availability:")
    check_port_2222()
    print()
    
    if docker_ok and python_docker_ok:
        print("✅ All checks passed! Integration tests should work.")
        return 0
    else:
        print("❌ Some checks failed. Integration tests may not work properly.")
        print("\nTo fix issues:")
        print("1. Install Docker: https://docs.docker.com/get-docker/")
        print("2. Start Docker daemon")
        print("3. Install Python Docker SDK: pip install docker")
        return 1

if __name__ == "__main__":
    sys.exit(main())