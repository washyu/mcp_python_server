#!/usr/bin/env python3
"""
Test SSH setup and verify AI doesn't hallucinate hardware specs when tools fail.

This test:
1. Sets up proper SSH authentication
2. Tests hardware discovery with correct credentials
3. Verifies AI doesn't hallucinate when SSH fails
"""

import asyncio
import aiohttp
import json
import re
import subprocess

class SSHHallucinationTest:
    def __init__(self):
        self.chat_url = "http://localhost:3001/api/chat"
        self.pi_ip = "192.168.50.41"
        self.pi_user = "shaun"
        
        # Known correct specs for Pi 5
        self.correct_specs = {
            "model": "Raspberry Pi 5",
            "ram": "16GB",
            "storage": "1TB NVMe",
            "cpu": "Broadcom BCM2712",
            "incorrect_specs": [
                "intel", "i7", "i9", "xeon", "amd", 
                "4GB", "8GB", "64GB eMMC", "SD card",
                "BCM2837", "BCM2711"  # Older Pi models
            ]
        }
    
    async def run_all_tests(self):
        """Run all SSH and hallucination tests."""
        print("🧪 SSH Setup and Hallucination Prevention Test Suite")
        print("=" * 60)
        
        # Test 1: Check current SSH access from container
        print("\n📋 Test 1: Verify SSH Access from Container")
        print("-" * 40)
        ssh_works = self._test_container_ssh()
        
        # Test 2: Test with wrong credentials (should fail gracefully)
        print("\n📋 Test 2: Test AI Response with Failed SSH")
        print("-" * 40)
        await self._test_failed_ssh_response()
        
        # Test 3: Test with setup attempt
        print("\n📋 Test 3: Test SSH Setup Tool")
        print("-" * 40)
        await self._test_ssh_setup()
        
        # Test 4: Hallucination detection
        print("\n📋 Test 4: Hallucination Detection")
        print("-" * 40)
        await self._test_hallucination_prevention()
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
    
    def _test_container_ssh(self) -> bool:
        """Test if container can SSH to Pi."""
        try:
            cmd = [
                "docker", "exec", "universal-homelab-mcp",
                "ssh", "-o", "StrictHostKeyChecking=no", 
                "-o", "ConnectTimeout=5",
                f"{self.pi_user}@{self.pi_ip}",
                "echo 'SSH test successful'"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Container can SSH to Pi 5")
                print(f"   Output: {result.stdout.strip()}")
                return True
            else:
                print("❌ Container cannot SSH to Pi 5")
                print(f"   Error: {result.stderr.strip()}")
                return False
                
        except Exception as e:
            print(f"❌ SSH test failed: {e}")
            return False
    
    async def _test_failed_ssh_response(self):
        """Test how AI responds when SSH fails."""
        # Use a non-existent IP to force failure
        test_message = "What are the hardware specs of the system at 192.168.50.99?"
        
        print(f"Testing with: {test_message}")
        print("Expected: AI should say SSH failed, not provide fake specs")
        print("-" * 40)
        
        response = await self._send_chat_request(test_message)
        self._analyze_response_for_hallucination(response, expect_failure=True)
    
    async def _test_ssh_setup(self):
        """Test SSH setup tool."""
        test_message = f"Set up SSH access to {self.pi_ip} with username {self.pi_user}"
        
        print(f"Testing with: {test_message}")
        print("-" * 40)
        
        response = await self._send_chat_request(test_message)
        
        # Check if AI uses setup tool
        if "setup_remote_ssh_access" in response:
            print("✅ AI attempts to use SSH setup tool")
        else:
            print("❌ AI doesn't use SSH setup tool")
    
    async def _test_hallucination_prevention(self):
        """Test that AI doesn't hallucinate Pi specs."""
        test_message = f"Get the hardware specs of the Raspberry Pi at {self.pi_ip}"
        
        print(f"Testing with: {test_message}")
        print("Checking for hallucinated specs...")
        print("-" * 40)
        
        response = await self._send_chat_request(test_message)
        self._analyze_response_for_hallucination(response, expect_failure=False)
    
    async def _send_chat_request(self, message: str) -> str:
        """Send a chat request and return full response."""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "messages": [{"role": "user", "content": message}],
                    "model": "llama3.1:8b",
                    "stream": True
                }
                
                full_response = ""
                
                async with session.post(self.chat_url, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as response:
                    if response.status != 200:
                        return f"Error: HTTP {response.status}"
                    
                    async for line in response.content:
                        line_text = line.decode('utf-8').strip()
                        if line_text.startswith('data: '):
                            try:
                                data = json.loads(line_text[6:])
                                if data.get('type') == 'text':
                                    content = data.get('content', '')
                                    full_response += content
                                    print(content, end='', flush=True)
                                elif data.get('type') == 'done':
                                    break
                            except json.JSONDecodeError:
                                continue
                
                print("\n")
                return full_response
                
        except Exception as e:
            return f"Request failed: {e}"
    
    def _analyze_response_for_hallucination(self, response: str, expect_failure: bool):
        """Analyze response for hallucinated hardware specs."""
        response_lower = response.lower()
        
        # Check for incorrect specs
        found_incorrect = []
        for spec in self.correct_specs["incorrect_specs"]:
            if spec.lower() in response_lower:
                found_incorrect.append(spec)
        
        # Check for tool usage
        uses_tool = "EXECUTE_TOOL:" in response
        admits_failure = any(phrase in response_lower for phrase in [
            "ssh failed", "cannot access", "failed to establish",
            "unable to determine", "authentication failed"
        ])
        
        # Check for correct Pi 5 specs
        mentions_pi5 = "raspberry pi 5" in response_lower or "pi 5" in response_lower
        mentions_16gb = "16gb" in response_lower or "15gi" in response_lower
        mentions_1tb = "1tb" in response_lower or "953" in response_lower
        
        print("\n📊 Analysis Results:")
        print(f"   Uses tool: {'✅' if uses_tool else '❌'}")
        print(f"   Admits SSH failure: {'✅' if admits_failure else '❌'}")
        print(f"   Hallucinated specs: {found_incorrect if found_incorrect else '✅ None'}")
        
        if not expect_failure:
            print(f"   Mentions Pi 5: {'✅' if mentions_pi5 else '❌'}")
            print(f"   Correct RAM (16GB): {'✅' if mentions_16gb else '❌'}")
            print(f"   Correct storage (1TB): {'✅' if mentions_1tb else '❌'}")
        
        # Overall assessment
        if expect_failure:
            if admits_failure and not found_incorrect:
                print("\n✅ PASS: AI correctly handles SSH failure without hallucination")
            else:
                print("\n❌ FAIL: AI hallucinated specs or didn't admit failure")
        else:
            if uses_tool and not found_incorrect:
                print("\n✅ PASS: AI uses tool without hallucination")
            else:
                print("\n❌ FAIL: AI hallucinated specs or didn't use tool")

async def setup_ssh_for_mcp():
    """Helper to set up SSH access for MCP container."""
    print("\n🔧 SSH Setup Helper")
    print("=" * 40)
    print("To enable SSH access from MCP container to your Pi 5:")
    print("\n1. Get the MCP container's public key:")
    print("   docker exec universal-homelab-mcp cat /root/.ssh/id_ed25519.pub")
    print("\n2. Add it to your Pi's authorized_keys:")
    print("   ssh shaun@192.168.50.41 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys'")
    print("   (Then paste the public key)")
    print("\n3. Or use the MCP SSH setup tool through the chat interface")
    print("=" * 40)

async def main():
    """Run the test suite."""
    tester = SSHHallucinationTest()
    
    # First show SSH setup instructions
    await setup_ssh_for_mcp()
    
    # Wait for user to be ready
    input("\nPress Enter when ready to run tests...")
    
    # Run tests
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())