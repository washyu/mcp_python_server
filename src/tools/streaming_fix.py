"""
Fix for streaming tool execution - accumulates response to find complete tool calls
"""

import re
import json
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class StreamingToolParser:
    """Accumulates streaming response and extracts complete tool calls."""
    
    def __init__(self):
        self.accumulated_response = ""
        self.tool_pattern = re.compile(
            r'\*\*EXECUTE_TOOL:\*\*\s+([\w-]+)\s+(\{[^}]*\})',
            re.DOTALL
        )
        
    def add_chunk(self, chunk: str) -> List[Tuple[str, dict]]:
        """
        Add a chunk to accumulated response and extract any complete tool calls.
        
        Returns:
            List of (tool_name, arguments) tuples for complete tool calls found
        """
        self.accumulated_response += chunk
        
        # Find all complete tool calls in accumulated response
        tool_calls = []
        for match in self.tool_pattern.finditer(self.accumulated_response):
            tool_name = match.group(1)
            args_str = match.group(2)
            
            try:
                # Try to parse JSON arguments
                arguments = json.loads(args_str)
                tool_calls.append((tool_name, arguments))
                
                # Remove this tool call from accumulated response
                # to avoid processing it again
                self.accumulated_response = self.accumulated_response.replace(
                    match.group(0), 
                    f"[Tool {tool_name} executed]"
                )
                
            except json.JSONDecodeError:
                # JSON not complete yet, keep accumulating
                continue
                
        return tool_calls
    
    def get_pending_content(self) -> str:
        """Get any accumulated content that's not part of a tool call."""
        # Remove incomplete tool calls from display
        pending = self.accumulated_response
        
        # Check if we have an incomplete tool call at the end
        if "**EXECUTE_TOOL:**" in pending:
            # Find the last occurrence
            last_tool_idx = pending.rfind("**EXECUTE_TOOL:**")
            
            # Check if this looks like an incomplete tool call
            remaining = pending[last_tool_idx:]
            if remaining.count("{") > remaining.count("}"):
                # Incomplete JSON, don't display this part yet
                return pending[:last_tool_idx]
                
        return pending
    
    def reset(self):
        """Reset the accumulated response."""
        self.accumulated_response = ""


def fix_streaming_in_chat(chat_interface):
    """
    Monkey patch the chat interface to fix streaming tool execution.
    This should be called before starting the chat.
    """
    original_query = chat_interface.query_ai_streaming
    
    async def fixed_query_ai_streaming(self, message: str, cancel_event=None):
        """Fixed version that accumulates response for tool parsing."""
        parser = StreamingToolParser()
        accumulated_for_display = ""
        
        async for chunk in original_query(message, cancel_event):
            # Add chunk to parser
            tool_calls = parser.add_chunk(chunk)
            
            # Execute any complete tool calls found
            for tool_name, arguments in tool_calls:
                logger.info(f"Executing tool from stream: {tool_name}")
                try:
                    result = await self.execute_mcp_tool(tool_name, arguments)
                    yield f"\n\n🔧 **Executed: {tool_name}**\n{result}\n\n"
                except Exception as e:
                    yield f"\n\n❌ **Failed: {tool_name}**\n{str(e)}\n\n"
            
            # Yield the displayable content
            # (excluding incomplete tool calls)
            new_content = parser.get_pending_content()
            if len(new_content) > len(accumulated_for_display):
                yield new_content[len(accumulated_for_display):]
                accumulated_for_display = new_content
    
    # Replace the method
    chat_interface.query_ai_streaming = fixed_query_ai_streaming.__get__(
        chat_interface, 
        chat_interface.__class__
    )