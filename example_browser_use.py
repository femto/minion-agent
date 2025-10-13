import os
import asyncio

import browser_use
from dotenv import load_dotenv
from minion_agent.config import AgentConfig, MCPStdio
from minion_agent.frameworks.minion_agent import MinionAgent
from minion_agent import MinionAgent, AgentConfig, AgentFramework
from smolagents import CodeAgent, AzureOpenAIServerModel
import minion_agent

# Load environment variables from .env file
load_dotenv()

async def main():
    # Get Azure configuration from environment variables
    azure_deployment = os.getenv('AZURE_DEPLOYMENT_NAME')
    api_version = os.getenv('OPENAI_API_VERSION')
    if not azure_deployment:
        raise ValueError("AZURE_DEPLOYMENT_NAME environment variable is not set")
    if not api_version:
        raise ValueError("OPENAI_API_VERSION environment variable is not set")

    # Create agent configuration
    config = AgentConfig(
        name="browser-agent",
        agent_type=CodeAgent,
        model_type=browser_use.ChatAzureOpenAI,
        model_id=azure_deployment,
        model_args={
            # "azure_deployment": azure_deployment,
            # "api_version": api_version,
        },
        tools=[
            #minion_agent.tools.browser_tool.browser,
            MCPStdio(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem","/Users/femtozheng/workspace","/Users/femtozheng/python-project/minion-agent"]
            )
        ],
        instructions="Compare the price of gpt-4o and DeepSeek-V3",
    )

    # Create and initialize the agent using MinionAgent.create_async
    agent = await MinionAgent.create_async(AgentFramework.BROWSER_USE, config)

    # Run the agent with a specific task
    result = await agent.run_async("Compare the price of gpt-4o and DeepSeek-V3 and create a detailed comparison table")
    print("Task Result:", result)
    #
    # # Run another task
    # result = await agent.run_async("Go to baidu.com, search for '人工智能最新进展', and summarize the top 3 results")
    # print("Task Result:", result)
    #result = await agent.run_async("打开微信公众号，发表一篇hello world")
    #print("Task Result:", result)

if __name__ == "__main__":
    # Verify environment variables
    required_vars = [
        'AZURE_OPENAI_ENDPOINT',
        'AZURE_OPENAI_API_KEY',
        'AZURE_DEPLOYMENT_NAME',
        'OPENAI_API_VERSION'
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("Error: Missing required environment variables:", missing_vars)
        print("Please set these variables in your .env file:")
        print("""
AZURE_OPENAI_ENDPOINT=your_endpoint_here
AZURE_OPENAI_API_KEY=your_key_here
AZURE_DEPLOYMENT_NAME=your_deployment_name_here
OPENAI_API_VERSION=your_api_version_here  # e.g. 2024-02-15
        """)
    else:
        asyncio.run(main()) 