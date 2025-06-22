#!/usr/bin/env python3
"""
Quick Hardware Discovery Test - Focus on tool usage and hallucination detection
"""

import asyncio
import aiohttp
import json
import re

async def quick_test():
    """Run a quick test to check tool usage and hallucination behavior."""
    
    url = "http://localhost:3001/api/chat"
    
    test_message = "What are the hardware specs of the system at 192.168.50.41?"
    
    payload = {
        "messages": [{"role": "user", "content": test_message}],
        "model": "llama3.1:8b", 
        "stream": True
    }
    
    print("🧪 Quick Hardware Discovery Test")
    print("=" * 50)
    print(f"Testing: {test_message}")
    print("-" * 50)
    
    full_response = ""
    tool_executed = False
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status != 200:
                    print(f"❌ HTTP Error: {response.status}")
                    return
                
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
                                tool_executed = True
                                print(f"\n🔧 {data.get('content', '')}")
                            elif data.get('type') == 'tool_result':
                                print(f"📊 {data.get('content', '')}")
                            elif data.get('type') == 'done':
                                break
                        except json.JSONDecodeError:
                            continue
    
    except asyncio.TimeoutError:
        print("\n⏰ Test timed out")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print("\n\n" + "=" * 50)
    print("📊 ANALYSIS")
    print("=" * 50)
    
    # Check tool usage
    tool_pattern = r'EXECUTE_TOOL:\s*discover_remote_system\s+IP:\s*192\.168\.50\.41'
    if re.search(tool_pattern, full_response):
        print("✅ Uses correct tool with proper template format")
    else:
        print("❌ Does not use correct tool format")
    
    # Check for hallucinations
    hallucination_patterns = [
        r'intel\s+i[79]-?\d+', r'intel\s+core\s+i[79]', r'msi\s+motherboard',
        r'rtx\s+\d+', r'gtx\s+\d+', r'geforce', r'nvidia'
    ]
    
    response_lower = full_response.lower()
    hallucinations = []
    
    for pattern in hallucination_patterns:
        matches = re.findall(pattern, response_lower)
        hallucinations.extend(matches)
    
    if hallucinations:
        print(f"❌ Hallucinated specs detected: {hallucinations}")
    else:
        print("✅ No obvious hallucinations detected")
    
    # Check for proper Pi indicators
    pi_patterns = [r'raspberry\s+pi', r'\bpi\b', r'arm', r'broadcom', r'cortex']
    pi_indicators = []
    
    for pattern in pi_patterns:
        matches = re.findall(pattern, response_lower)
        pi_indicators.extend(matches)
    
    if pi_indicators:
        print(f"✅ Raspberry Pi indicators found: {pi_indicators}")
    else:
        print("⚠️  No Raspberry Pi indicators (may be normal if tool failed)")
    
    # Tool execution status
    if tool_executed:
        print("✅ Tool execution was attempted")
    else:
        print("❌ No tool execution detected")
    
    print(f"\n📝 Response length: {len(full_response)} characters")
    
    # Check if response contains both tool execution AND post-failure hallucination
    has_tool_execution = "EXECUTE_TOOL:" in full_response
    has_post_failure_content = "Tool Result:" in full_response and len(full_response.split("Tool Result:")[-1]) > 100
    
    if has_tool_execution and has_post_failure_content:
        print("⚠️  AI continues generating content after tool failure - potential hallucination risk")
    
    return {
        "tool_used": bool(re.search(tool_pattern, full_response)),
        "tool_executed": tool_executed,
        "hallucinations": hallucinations,
        "pi_indicators": pi_indicators,
        "response_length": len(full_response)
    }

if __name__ == "__main__":
    asyncio.run(quick_test())