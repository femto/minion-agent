#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MCP Agent Integration Example with Auto-Converted Raw Functions

This example demonstrates:
1. How to integrate MCP filesystem toolset with a minion agent
2. How to use raw Python functions alongside MCP tools
3. Automatic conversion of raw functions to BaseTool/AsyncBaseTool during agent setup

Key features shown:
- MCP filesystem tools (pre-converted)
- Raw sync function (calc) → auto-converted to BaseTool
- Raw async function (async_func) → auto-converted to AsyncBaseTool
- Seamless integration of all tool types
"""

import asyncio
import logging
from pathlib import Path
from typing import Union

from minion.agents import CodeAgent
from minion.tools.mcp.mcp_toolset import create_filesystem_toolset
from minion.agents.base_agent import BaseAgent
from minion.providers.openai_provider import OpenAIProvider

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Raw functions that will be auto-converted to tools
def calc(expression: str) -> float:
    """
    Calculate the result of a mathematical expression.
    
    Args:
        expression: Mathematical expression to evaluate (e.g., "2 + 3 * 4")
    """
    try:
        # Simple safe evaluation for basic math
        allowed_chars = set('0123456789+-*/.() ')
        if all(c in allowed_chars for c in expression):
            result = eval(expression)
            return float(result)
        else:
            raise ValueError("Expression contains invalid characters")
    except Exception as e:
        raise ValueError(f"Invalid expression: {e}")


async def async_func(message: str, delay: float = 1.0) -> str:
    """
    Process a message asynchronously with a delay.
    
    Args:
        message: The message to process
        delay: Delay in seconds before processing (default 1.0)
    """
    print(f"⏳ Processing message '{message}' with {delay}s delay...")
    await asyncio.sleep(delay)
    processed = f"Processed: {message.upper()} (delayed by {delay}s)"
    print(f"✅ Processing complete!")
    return processed


async def main():
    """Main example function showing MCP integration with agent"""
    
    try:
        # Create MCP filesystem toolset (async - automatically sets up)
        print("Creating and setting up MCP filesystem toolset...")
        workspace_paths = [str(Path(__file__).parent.parent.parent)]  # Project root
        mcp_toolset = await create_filesystem_toolset(
            workspace_paths=workspace_paths,
            name="agent_mcp_filesystem_toolset"
        )
        
        if not mcp_toolset.is_healthy:
            print(f"❌ MCP toolset setup failed: {mcp_toolset.setup_error}")
            return
            
        print(f"✅ MCP toolset ready with {len(mcp_toolset.tools)} tools")
        
        # Get MCP tools
        mcp_tools = mcp_toolset.get_tools()
        
        # Add simple raw functions (minion will auto-convert them to tools during setup)
        # - calc: sync function → will become BaseTool
        # - async_func: async function → will become AsyncBaseTool
        custom_tools = [calc, async_func]
        
        # Combine all tools: MCP tools (already converted) + raw functions (will be auto-converted)
        all_tools = mcp_tools + custom_tools
        
        print(f"📦 Total tools before setup: {len(all_tools)} (MCP: {len(mcp_tools)}, Custom: {len(custom_tools)})")
        
        # Create agent with all tools (MCP + custom functions)
        # The raw functions will be automatically converted during agent.setup()
        agent = await CodeAgent.create(
            llm="gpt-4o",
            tools=all_tools,
            name="Enhanced MCP Agent"
        )
        
        print(f"🔧 Agent setup complete! Final tool count: {len(agent.tools)}")
        print("📋 Available tools:")
        for tool in agent.tools:
            tool_type = "AsyncBaseTool" if hasattr(tool, 'forward') and asyncio.iscoroutinefunction(tool.forward) else "BaseTool"
            if hasattr(tool, '__class__') and 'Mcp' in tool.__class__.__name__:
                tool_type = "MCP Tool"
            print(f"  - {tool.name}: {tool_type}")
            print(f"    {tool.description}")
        print()
        
        # Example conversations
        print("\n🤖 Starting conversation with enhanced MCP agent...")
        
        # Test filesystem operations
        print("\n📁 Testing filesystem operations:")
        response = await agent.run_async("Can you list the files in the current directory?")
        print(response.answer)
        
        # Test synchronous calc tool
        print("\n🧮 Testing synchronous calc tool:")
        response = await agent.run_async("Calculate 15 + 27 using the calc tool")
        print(response.answer)
        
        # Test asynchronous func tool
        print("\n⚡ Testing asynchronous func tool:")
        response = await agent.run_async("Use the async_func tool to process the message 'hello world' with a 2 second delay")
        print(response.answer)
            
    except Exception as e:
        print(f"❌ Error during MCP agent example: {e}")
        logger.exception("Full error details:")
        
    finally:
        # Clean up
        if 'mcp_toolset' in locals():
            print("Cleaning up MCP toolset...")
            await mcp_toolset.close()


if __name__ == "__main__":
    asyncio.run(main())