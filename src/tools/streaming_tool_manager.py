"""
Streaming Tool Manager - Handles tool execution callbacks during streaming
"""

import asyncio
import re
import json
import logging
from typing import AsyncGenerator, Callable, Dict, List, Any, Optional, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Represents a parsed tool call"""
    tool_name: str
    arguments: Dict[str, Any]
    start_pos: int
    end_pos: int
    raw_text: str


class StreamingToolManager:
    """Manages tool execution callbacks during streaming response"""
    
    def __init__(self, tool_executor: Callable[[str, Dict[str, Any]], Any]):
        self.tool_executor = tool_executor
        self.buffer = ""
        self.executed_tools: Set[str] = set()
        self.tool_pattern = re.compile(
            r'(?:\*\*EXECUTE_TOOL:\*\*|`EXECUTE_TOOL:`)\s+([\w-]+)\s+(\{(?:[^{}]|{[^{}]*})*\})',
            re.DOTALL
        )
        
    def add_chunk(self, chunk: str) -> tuple[str, List[ToolCall]]:
        """
        Add chunk to buffer and return (display_chunk, new_tool_calls)
        
        Returns:
            display_chunk: What should be displayed to user
            new_tool_calls: Complete tool calls found in this update
        """
        self.buffer += chunk
        
        # Find all complete tool calls in current buffer
        current_tools = self._find_complete_tools()
        
        # Filter out already executed tools
        new_tools = []
        for tool in current_tools:
            tool_signature = f"{tool.tool_name}:{json.dumps(tool.arguments, sort_keys=True)}"
            if tool_signature not in self.executed_tools:
                new_tools.append(tool)
                self.executed_tools.add(tool_signature)
        
        # Return the chunk for immediate display and any new tools
        return chunk, new_tools
    
    def _find_complete_tools(self) -> List[ToolCall]:
        """Find all complete tool calls in the current buffer"""
        tools = []
        
        for match in self.tool_pattern.finditer(self.buffer):
            tool_name = match.group(1)
            args_str = match.group(2)
            
            try:
                # Parse JSON arguments directly
                arguments = json.loads(args_str)
                
                tools.append(ToolCall(
                    tool_name=tool_name,
                    arguments=arguments,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    raw_text=match.group(0)
                ))
                
            except json.JSONDecodeError as e:
                # JSON incomplete or malformed, log for debugging
                logger.debug(f"JSON parse error for tool {tool_name}: {args_str} - {e}")
                continue
                
        return tools
    
    
    async def execute_tool_with_callback(
        self, 
        tool_call: ToolCall,
        callback: Callable[[str], None]
    ) -> str:
        """Execute a tool and call callback with the result"""
        try:
            logger.info(f"🔧 Executing tool: {tool_call.tool_name}")
            result = await self.tool_executor(tool_call.tool_name, tool_call.arguments)
            
            # Format result for display
            formatted_result = f"\n\n🔧 **Tool Result: {tool_call.tool_name}**\n{result}\n"
            
            # Call callback immediately
            if callback:
                callback(formatted_result)
            
            return formatted_result
            
        except Exception as e:
            error_msg = f"\n\n❌ **Tool Error ({tool_call.tool_name}):** {str(e)}\n"
            logger.error(f"Tool execution failed: {e}")
            
            if callback:
                callback(error_msg)
                
            return error_msg


async def stream_with_tool_execution(
    response_stream: AsyncGenerator[str, None],
    tool_executor: Callable[[str, Dict[str, Any]], Any],
    output_callback: Callable[[str], None],
    cancel_event: Optional[asyncio.Event] = None
) -> AsyncGenerator[str, None]:
    """
    Stream response with synchronized tool execution
    
    Args:
        response_stream: Original AI response stream
        tool_executor: Function to execute MCP tools
        output_callback: Callback for immediate output (for UI updates)
        cancel_event: Event to cancel streaming
        
    Yields:
        Chunks of text including tool execution results
    """
    
    tool_manager = StreamingToolManager(tool_executor)
    
    try:
        async for chunk in response_stream:
            # Check for cancellation
            if cancel_event and cancel_event.is_set():
                yield "\n\n⏹️ Response cancelled by user"
                break
            
            if not chunk or not chunk.strip():
                continue
                
            # Add chunk to tool manager and get any new tool calls
            display_chunk, new_tools = tool_manager.add_chunk(chunk)
            
            # Yield the chunk immediately for display
            yield display_chunk
            
            # Execute any new tools found (don't await - run in background)
            for tool_call in new_tools:
                # Create a callback that yields tool results
                def make_tool_callback():
                    async def tool_callback(result: str):
                        # This will be called when tool completes
                        output_callback(result) if output_callback else None
                        
                    return tool_callback
                
                # Execute tool in background and yield result when ready
                try:
                    result = await tool_manager.execute_tool_with_callback(
                        tool_call, 
                        None  # We'll yield directly instead of using callback
                    )
                    yield result
                    
                except Exception as e:
                    yield f"\n\n❌ **Tool Error:** {str(e)}\n"
        
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield f"\n\n❌ Streaming error: {str(e)}"