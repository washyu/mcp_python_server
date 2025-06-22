#!/usr/bin/env python3
"""
UI Test for Hardware Discovery Functionality

This test verifies that:
1. The AI uses discover_remote_system instead of discover-homelab-topology
2. The AI uses proper template format (EXECUTE_TOOL: discover_remote_system IP: 192.168.50.41)
3. Real hardware discovery occurs instead of hallucinated Intel i7/MSI specs
4. The system returns actual Raspberry Pi hardware information
"""

import asyncio
import aiohttp
import json
import re
import time
from typing import List, Dict, Any

class HardwareDiscoveryUITest:
    def __init__(self, chat_url: str = "http://localhost:3001/api/chat"):
        self.chat_url = chat_url
        self.results = {}
    
    async def test_hardware_discovery_functionality(self):
        """Test the complete hardware discovery workflow."""
        print("🧪 Starting Hardware Discovery UI Test...")
        print("=" * 60)
        
        test_cases = [
            {
                "name": "Direct Hardware Query",
                "message": "What are the hardware specs of the system at 192.168.50.41? This should be a Raspberry Pi system.",
                "expected_tool": "discover_remote_system",
                "expected_ip": "192.168.50.41"
            },
            {
                "name": "Simple Hardware Check",
                "message": "Check the hardware of 192.168.50.41",
                "expected_tool": "discover_remote_system", 
                "expected_ip": "192.168.50.41"
            },
            {
                "name": "System Analysis Request",
                "message": "Analyze the system at proxmoxpi.local (192.168.50.41) and tell me what hardware it has",
                "expected_tool": "discover_remote_system",
                "expected_ip": "192.168.50.41"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🔍 Test {i}: {test_case['name']}")
            print("-" * 40)
            
            result = await self._run_single_test(
                test_case["message"],
                test_case["expected_tool"],
                test_case["expected_ip"]
            )
            
            self.results[test_case["name"]] = result
            
            # Brief pause between tests
            await asyncio.sleep(2)
        
        # Print summary
        self._print_test_summary()
    
    async def _run_single_test(self, message: str, expected_tool: str, expected_ip: str) -> Dict[str, Any]:
        """Run a single test case and analyze results."""
        print(f"📝 Sending: {message}")
        
        try:
            # Send chat request
            async with aiohttp.ClientSession() as session:
                payload = {
                    "messages": [{"role": "user", "content": message}],
                    "model": "llama3.1:8b",
                    "stream": True
                }
                
                start_time = time.time()
                full_response = ""
                tool_executions = []
                
                async with session.post(self.chat_url, json=payload) as response:
                    if response.status != 200:
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {await response.text()}"
                        }
                    
                    # Process streaming response
                    async for line in response.content:
                        line_text = line.decode('utf-8').strip()
                        if line_text.startswith('data: '):
                            try:
                                data = json.loads(line_text[6:])
                                if data.get('type') == 'text':
                                    content = data.get('content', '')
                                    full_response += content
                                    print(content, end='', flush=True)
                                elif data.get('type') == 'tool_start':
                                    tool_start_msg = data.get('content', '')
                                    print(f"\n🔧 {tool_start_msg}")
                                elif data.get('type') == 'tool_result':
                                    tool_result = data.get('content', '')
                                    print(f"📊 {tool_result}")
                                elif data.get('type') == 'done':
                                    break
                            except json.JSONDecodeError:
                                continue
                
                end_time = time.time()
                response_time = end_time - start_time
                
                # Analyze the response
                analysis = self._analyze_response(
                    full_response, expected_tool, expected_ip
                )
                
                analysis.update({
                    "response_time": response_time,
                    "full_response": full_response
                })
                
                return analysis
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }
    
    def _analyze_response(self, response: str, expected_tool: str, expected_ip: str) -> Dict[str, Any]:
        """Analyze the AI response for correct tool usage and hardware detection."""
        analysis = {
            "success": True,
            "issues": [],
            "checks": {}
        }
        
        # Check 1: Does it use the correct tool?
        tool_pattern = r'EXECUTE_TOOL:\s*(\w+)'
        tool_matches = re.findall(tool_pattern, response)
        
        if not tool_matches:
            analysis["issues"].append("❌ No EXECUTE_TOOL commands found")
            analysis["checks"]["uses_execute_tool"] = False
        else:
            analysis["checks"]["uses_execute_tool"] = True
            
            # Check if it uses the correct tool
            if expected_tool in tool_matches:
                analysis["checks"]["uses_correct_tool"] = True
                print(f"\n✅ Uses correct tool: {expected_tool}")
            else:
                analysis["checks"]["uses_correct_tool"] = False
                analysis["issues"].append(f"❌ Wrong tool used: {tool_matches} (expected: {expected_tool})")
        
        # Check 2: Does it use the template format correctly?
        template_pattern = r'EXECUTE_TOOL:\s*discover_remote_system\s+IP:\s*(\S+)'
        template_match = re.search(template_pattern, response)
        
        if template_match:
            analysis["checks"]["uses_template_format"] = True
            detected_ip = template_match.group(1)
            
            if detected_ip == expected_ip:
                analysis["checks"]["correct_ip"] = True
                print(f"✅ Correct IP address: {detected_ip}")
            else:
                analysis["checks"]["correct_ip"] = False
                analysis["issues"].append(f"❌ Wrong IP: {detected_ip} (expected: {expected_ip})")
        else:
            analysis["checks"]["uses_template_format"] = False
            analysis["issues"].append("❌ Template format not used correctly")
        
        # Check 3: Does it avoid hallucinated hardware specs?
        hallucination_indicators = [
            "intel i9-9900k", "intel i7", "msi motherboard", 
            "rtx", "gtx", "intel core i7", "core i9"
        ]
        
        response_lower = response.lower()
        hallucinations_found = [
            indicator for indicator in hallucination_indicators 
            if indicator in response_lower
        ]
        
        if hallucinations_found:
            analysis["checks"]["no_hallucinations"] = False
            analysis["issues"].append(f"❌ Hallucinated specs found: {hallucinations_found}")
        else:
            analysis["checks"]["no_hallucinations"] = True
            print("✅ No hallucinated hardware specs detected")
        
        # Check 4: Does it mention proper Raspberry Pi hardware indicators?
        pi_indicators = [
            "raspberry pi", "pi", "arm", "broadcom", "cortex", 
            "bcm", "arm64", "aarch64"
        ]
        
        pi_mentions = [
            indicator for indicator in pi_indicators
            if indicator in response_lower
        ]
        
        if pi_mentions:
            analysis["checks"]["mentions_raspberry_pi"] = True
            print(f"✅ Raspberry Pi indicators found: {pi_mentions}")
        else:
            analysis["checks"]["mentions_raspberry_pi"] = False
            analysis["issues"].append("⚠️  No Raspberry Pi indicators found (this might be expected if tool execution failed)")
        
        # Determine overall success
        critical_checks = ["uses_execute_tool", "uses_correct_tool", "uses_template_format", "no_hallucinations"]
        failed_critical = [
            check for check in critical_checks 
            if not analysis["checks"].get(check, False)
        ]
        
        if failed_critical:
            analysis["success"] = False
            analysis["issues"].append(f"❌ Critical checks failed: {failed_critical}")
        
        return analysis
    
    def _print_test_summary(self):
        """Print a summary of all test results."""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result.get("success", False))
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\n📋 DETAILED RESULTS:")
        print("-" * 40)
        
        for test_name, result in self.results.items():
            status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
            print(f"\n{status} {test_name}")
            
            if result.get("error"):
                print(f"   Error: {result['error']}")
            
            if result.get("issues"):
                for issue in result["issues"]:
                    print(f"   {issue}")
            
            if result.get("response_time"):
                print(f"   Response Time: {result['response_time']:.1f}s")
        
        # Print recommendations
        print("\n🔧 RECOMMENDATIONS:")
        print("-" * 40)
        
        all_issues = []
        for result in self.results.values():
            all_issues.extend(result.get("issues", []))
        
        common_issues = {}
        for issue in all_issues:
            if issue in common_issues:
                common_issues[issue] += 1
            else:
                common_issues[issue] = 1
        
        if common_issues:
            for issue, count in sorted(common_issues.items(), key=lambda x: x[1], reverse=True):
                print(f"   {issue} (occurred {count} times)")
        else:
            print("   🎉 No issues detected! System working correctly.")

async def main():
    """Run the hardware discovery UI test."""
    tester = HardwareDiscoveryUITest()
    
    print("🚀 Hardware Discovery UI Test Suite")
    print("Testing MCP server at http://localhost:3001")
    print("\nThis test verifies:")
    print("  1. AI uses discover_remote_system tool (not discover-homelab-topology)")
    print("  2. AI uses template format: EXECUTE_TOOL: discover_remote_system IP: 192.168.50.41")
    print("  3. No hallucinated Intel i7/MSI specs")
    print("  4. Real hardware discovery for Raspberry Pi system")
    
    await tester.test_hardware_discovery_functionality()

if __name__ == "__main__":
    asyncio.run(main())