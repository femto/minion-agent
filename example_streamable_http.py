"""Example usage of Minion Agent with Streamable HTTP MCP tool."""

import asyncio
import logging
import os
from dotenv import load_dotenv

from minion_agent import MinionAgent, AgentConfig, AgentFramework
from minion_agent.config import MCPStreamableHttp
from minion_agent.logging import setup_logger

from minion.agents import (
    CodeAgent,
    ToolCallingAgent,
)

# Load environment variables from .env file
load_dotenv()

# Configure the agent with streamable HTTP MCP tool
agent_config = AgentConfig(
    model_id=os.environ.get("AZURE_DEPLOYMENT_NAME"),
    name="streamable_http_assistant",
    description="A helpful assistant with streamable HTTP capabilities",
    model_args={
        "azure_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT"),
        "api_key": os.environ.get("AZURE_OPENAI_API_KEY"),
        "api_version": os.environ.get("OPENAI_API_VERSION"),
        "model": "gpt-4o",  # Actual model to use in minion framework
    },
    tools=[
        # Add streamable HTTP MCP tool pointing to localhost:3000/mcp
        MCPStreamableHttp(
            url="http://localhost:3000/mcp"
        ),
    ],
    agent_type=CodeAgent,
)

async def main():
    try:
        # Create and run the agent
        agent = await MinionAgent.create_async(AgentFramework.EXTERNAL_MINION_AGENT, agent_config)
        
        # Test the streamable HTTP tool
        result = await agent.run_async("Test the streamable HTTP tool and show me what capabilities it has")
        
        print("Agent's response:", result.final_output.content)
        print("done")

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    asyncio.run(main())