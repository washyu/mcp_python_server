#!/usr/bin/env python3
"""
Test subprocess communication with the MCP server.
"""

import asyncio
import subprocess
import json


async def test_subprocess():
    """Test basic subprocess communication."""
    print("Starting MCP server as subprocess...")
    
    # Start the server
    proc = await asyncio.create_subprocess_exec(
        "uv", "run", "python", "main.py",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,  # Ignore stderr for cleaner output
        cwd="/home/shaun/workspace/mcp_python_server"
    )
    
    # Give it time to start
    await asyncio.sleep(1)
    
    # Send initialize request
    request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "0.1.0",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "0.1.0"
            }
        },
        "id": 1
    }
    
    request_str = json.dumps(request) + "\n"
    print(f"Sending: {request_str.strip()}")
    
    proc.stdin.write(request_str.encode())
    await proc.stdin.drain()
    
    # Try to read response
    try:
        response_line = await asyncio.wait_for(proc.stdout.readline(), timeout=3)
        if response_line:
            print(f"Response: {response_line.decode().strip()}")
        else:
            print("No response received")
            
        # Check stderr
        stderr = await proc.stderr.read(1000)
        if stderr:
            print(f"Stderr: {stderr.decode()}")
            
    except asyncio.TimeoutError:
        print("Timeout waiting for response")
        
        # Check if process is still running
        if proc.returncode is not None:
            print(f"Process exited with code: {proc.returncode}")
            stderr = await proc.stderr.read()
            print(f"Stderr: {stderr.decode()}")
    
    finally:
        proc.terminate()
        await proc.wait()


if __name__ == "__main__":
    asyncio.run(test_subprocess())