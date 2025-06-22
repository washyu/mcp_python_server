#!/usr/bin/env python3
"""
Specific test for Raspberry Pi 5 hallucination issue.

Tests that AI:
1. Doesn't provide Intel/AMD specs for a Raspberry Pi
2. Doesn't provide older Pi specs (BCM2837, BCM2711)
3. Reports correct Pi 5 specs when SSH works
4. Reports SSH failure when it can't connect
"""

import asyncio
import aiohttp
import json
import re
from typing import Dict, List

class Pi5HallucinationTest:
    def __init__(self):
        self.chat_url = "http://localhost:3001/api/chat"
        self.results = []
        
        # Hallucination patterns to detect
        self.hallucination_patterns = {
            "intel_specs": [
                r"intel.*i[3579]", r"core.*i[3579]", r"xeon", 
                r"coffee lake", r"comet lake", r"alder lake"
            ],
            "amd_specs": [
                r"amd.*ryzen", r"epyc", r"threadripper"
            ],
            "wrong_pi_models": [
                r"bcm283[567]", r"bcm2711", r"cortex-a53", r"cortex-a72",
                r"raspberry pi [234]", r"pi [234] model"
            ],
            "wrong_ram": [
                r"[1248] ?gb", r"ddr3", r"64 ?gb", r"emmc"
            ],
            "wrong_storage": [
                r"sd card", r"16 ?gb", r"32 ?gb", r"64 ?gb", r"microsd"
            ]
        }
        
        # Correct Pi 5 patterns
        self.correct_patterns = {
            "model": [r"raspberry pi 5", r"pi 5 model b", r"bcm2712"],
            "ram": [r"16 ?gb", r"15 ?gi", r"lpddr4x"],
            "storage": [r"1 ?tb", r"953", r"nvme", r"inland"]
        }
    
    async def run_tests(self):
        """Run all Pi 5 hallucination tests."""
        print("🧪 Raspberry Pi 5 Hallucination Test Suite")
        print("=" * 60)
        
        test_cases = [
            {
                "name": "Direct IP query",
                "query": "What are the hardware specs of the system at 192.168.50.41?",
                "expected": "Should use discover_remote_system and handle SSH failure properly"
            },
            {
                "name": "Pi identification query",
                "query": "Tell me about the Raspberry Pi at 192.168.50.41",
                "expected": "Should recognize it's a Pi and not provide Intel/AMD specs"
            },
            {
                "name": "Specific Pi 5 query",
                "query": "Get the specs of the Raspberry Pi 5 at 192.168.50.41",
                "expected": "Should attempt discovery, not assume older Pi specs"
            }
        ]
        
        for test in test_cases:
            print(f"\n📋 Test: {test['name']}")
            print(f"Query: {test['query']}")
            print(f"Expected: {test['expected']}")
            print("-" * 60)
            
            result = await self._test_query(test['query'])
            self.results.append({
                "test": test['name'],
                "result": result
            })
        
        # Print summary
        self._print_summary()
    
    async def _test_query(self, query: str) -> Dict:
        """Test a single query and analyze response."""
        try:
            response = await self._send_chat_request(query)
            analysis = self._analyze_response(response)
            
            # Print immediate results
            self._print_analysis(analysis)
            
            return {
                "success": analysis["passed"],
                "response": response,
                "analysis": analysis
            }
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _send_chat_request(self, message: str) -> str:
        """Send chat request and collect full response."""
        async with aiohttp.ClientSession() as session:
            payload = {
                "messages": [{"role": "user", "content": message}],
                "model": "llama3.1:8b",
                "stream": True
            }
            
            full_response = ""
            
            async with session.post(self.chat_url, json=payload) as response:
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
                        except:
                            continue
            
            print("\n")
            return full_response
    
    def _analyze_response(self, response: str) -> Dict:
        """Analyze response for hallucinations and correct behavior."""
        response_lower = response.lower()
        
        analysis = {
            "uses_tool": bool(re.search(r'EXECUTE_TOOL:\s*discover_remote_system', response)),
            "admits_ssh_failure": any(phrase in response_lower for phrase in [
                "ssh failed", "cannot access", "failed to establish",
                "unable to determine", "authentication failed", 
                "ssh access", "cannot connect"
            ]),
            "hallucinations": {},
            "correct_specs": {},
            "passed": False
        }
        
        # Check for hallucinations
        for category, patterns in self.hallucination_patterns.items():
            matches = []
            for pattern in patterns:
                if re.search(pattern, response_lower):
                    matches.append(pattern)
            if matches:
                analysis["hallucinations"][category] = matches
        
        # Check for correct specs (only if claiming success)
        if not analysis["admits_ssh_failure"]:
            for category, patterns in self.correct_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, response_lower):
                        analysis["correct_specs"][category] = True
                        break
        
        # Determine pass/fail
        no_hallucinations = len(analysis["hallucinations"]) == 0
        proper_failure_handling = analysis["admits_ssh_failure"] or analysis["uses_tool"]
        
        analysis["passed"] = no_hallucinations and proper_failure_handling
        
        return analysis
    
    def _print_analysis(self, analysis: Dict):
        """Print analysis results."""
        print("\n🔍 Analysis:")
        print(f"   Tool usage: {'✅ Yes' if analysis['uses_tool'] else '❌ No'}")
        print(f"   Admits SSH failure: {'✅ Yes' if analysis['admits_ssh_failure'] else '❌ No'}")
        
        if analysis["hallucinations"]:
            print("   ❌ Hallucinations detected:")
            for category, matches in analysis["hallucinations"].items():
                print(f"      - {category}: {matches}")
        else:
            print("   ✅ No hallucinations detected")
        
        if analysis["correct_specs"]:
            print("   ✅ Correct specs mentioned:")
            for spec in analysis["correct_specs"]:
                print(f"      - {spec}")
        
        print(f"\n   Overall: {'✅ PASS' if analysis['passed'] else '❌ FAIL'}")
    
    def _print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.results if r.get("result", {}).get("success", False))
        total = len(self.results)
        
        print(f"Total tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success rate: {(passed/total)*100:.0f}%")
        
        print("\n🎯 Key Findings:")
        
        # Collect all hallucinations
        all_hallucinations = set()
        for result in self.results:
            if result.get("result", {}).get("analysis", {}).get("hallucinations"):
                for category, matches in result["result"]["analysis"]["hallucinations"].items():
                    all_hallucinations.add(category)
        
        if all_hallucinations:
            print("❌ Common hallucinations:")
            for h in all_hallucinations:
                print(f"   - {h}")
        else:
            print("✅ No hallucinations detected across all tests!")
        
        # Check tool usage
        tool_usage = sum(1 for r in self.results 
                        if r.get("result", {}).get("analysis", {}).get("uses_tool", False))
        print(f"\n🔧 Tool usage: {tool_usage}/{total} tests")
        
        # SSH failure handling
        ssh_handling = sum(1 for r in self.results 
                          if r.get("result", {}).get("analysis", {}).get("admits_ssh_failure", False))
        print(f"🔐 Proper SSH failure handling: {ssh_handling}/{total} tests")

async def main():
    """Run Pi 5 hallucination tests."""
    print("🍓 Testing Raspberry Pi 5 Hardware Discovery")
    print("This test verifies the AI doesn't hallucinate Intel/AMD specs")
    print("or incorrect Pi models when discovering Pi 5 hardware.\n")
    
    tester = Pi5HallucinationTest()
    await tester.run_tests()

if __name__ == "__main__":
    asyncio.run(main())