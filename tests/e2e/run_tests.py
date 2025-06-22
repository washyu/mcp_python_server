#!/usr/bin/env python3
"""
E2E Test Runner for MCP Server
"""

import asyncio
import subprocess
import sys
from pathlib import Path

async def run_test(test_file: str, description: str):
    """Run a single test file."""
    print(f"\n🧪 Running: {description}")
    print("-" * 50)
    
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent  # Run from project root
        )
        
        if result.returncode == 0:
            print(f"✅ {description}: PASSED")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"❌ {description}: FAILED")
            if result.stderr:
                print(f"Error: {result.stderr}")
            if result.stdout:
                print(f"Output: {result.stdout}")
            return False
            
    except Exception as e:
        print(f"❌ {description}: ERROR - {e}")
        return False
    
    return True

async def main():
    """Run all E2E tests."""
    print("🚀 MCP Server E2E Test Suite")
    print("=" * 60)
    
    # Define tests to run
    tests = [
        ("tests/e2e/test_system.py", "System Health Check"),
        ("tests/e2e/test_quick_hardware_discovery.py", "Hardware Discovery"),
        # Add more tests as needed
    ]
    
    results = []
    for test_file, description in tests:
        result = await run_test(test_file, description)
        results.append((description, result))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for description, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {description}")
    
    print(f"\nTotal: {passed}/{total} passed ({(passed/total)*100:.0f}%)")
    
    if passed < total:
        print("\n❌ Some tests failed!")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")

if __name__ == "__main__":
    asyncio.run(main())