"""Example usage of Minion Agent."""

import asyncio
import logging

from dotenv import load_dotenv
import os
from PIL import Image
from io import BytesIO
from time import sleep
from typing import List, Dict, Optional
from smolagents import (Tool, ChatMessage, GradioUI)
from smolagents.models import parse_json_if_needed
from custom_azure_model import CustomAzureOpenAIServerModel
import minion_agent
from minion_agent.config import MCPStdio, MCPSse
from minion_agent.logging import setup_logger
from minion_agent.tools.run_apple_script import run_applescript, run_applescript_capture, run_command

def parse_tool_args_if_needed(message: ChatMessage) -> ChatMessage:
    for tool_call in message.tool_calls:
        tool_call.function.arguments = parse_json_if_needed(tool_call.function.arguments)
    return message

# Load environment variables from .env file
load_dotenv()

from minion_agent import MinionAgent, AgentConfig, AgentFramework

from smolagents import (
    CodeAgent,
    ToolCallingAgent,
    DuckDuckGoSearchTool,
    VisitWebpageTool,
    AzureOpenAIServerModel, ActionStep,
)

# Set up screenshot callback for Playwright
# def save_screenshot(memory_step: ActionStep, agent: CodeAgent) -> None:
#     sleep(1.0)  # Let JavaScript animations happen before taking the screenshot
#
#     # Get the browser tool
#     browser_tool = agent.tools.get("browser")
#     if browser_tool:
#         # Clean up old screenshots to save memory
#         for previous_memory_step in agent.memory.steps:
#             if isinstance(previous_memory_step, ActionStep) and previous_memory_step.step_number <= memory_step.step_number - 2:
#                 previous_memory_step.observations_images = None
#
#         # Take screenshot using Playwright
#         result = browser_tool(action="screenshot")
#         if result["success"] and "screenshot" in result.get("data", {}):
#             # Convert bytes to PIL Image
#             screenshot_bytes = result["data"]["screenshot"]
#             image = Image.open(BytesIO(screenshot_bytes))
#             print(f"Captured a browser screenshot: {image.size} pixels")
#             memory_step.observations_images = [image.copy()]  # Create a copy to ensure it persists
#
#         # Get current URL
#         state_result = browser_tool(action="get_current_state")
#         if state_result["success"] and "url" in state_result.get("data", {}):
#             url_info = f"Current url: {state_result['data']['url']}"
#             memory_step.observations = (
#                 url_info if memory_step.observations is None else memory_step.observations + "\n" + url_info
#             )

# Configure the agent
agent_config = AgentConfig(
    model_id=os.environ.get("AZURE_DEPLOYMENT_NAME"),
    name="research_assistant",
    description="A helpful research assistant",
    model_args={"azure_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT"),
                "api_key": os.environ.get("AZURE_OPENAI_API_KEY"),
                "api_version": os.environ.get("OPENAI_API_VERSION"),
                },
    tools=[
        #minion_agent.tools.browser_tool.browser,
run_applescript,run_applescript_capture,run_command,
        MCPStdio(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem","/Users/femtozheng/workspace","/Users/femtozheng/python-project/minion-agent"]
        ),
# MCPStdio(
#             command="npx",
#             args=["-y", "@smithery/cli@latest", "run", "@Dhravya/apple-mcp","--key","431d6d12-c9ea-4a6d-a033-f9ddbe0ae7e1"]
#         ),

    ],
    model_type=AzureOpenAIServerModel,  # Updated to use our custom model
    #model_type="CustomAzureOpenAIServerModel",  # Updated to use our custom model
    agent_type=CodeAgent,
    agent_args={"additional_authorized_imports":"*",
                #"planning_interval":3
#"step_callbacks":[save_screenshot]
                }
)
# setup_logger(logging.DEBUG)
async def main():
    try:
        # Create and run the agent
        agent = await MinionAgent.create_async(AgentFramework.SMOLAGENTS, agent_config)
        upload_folder = "./uploaded_files"
        os.makedirs(upload_folder, exist_ok=True)
        gradio_ui = GradioUI(
            agent=agent._agent,
            file_upload_folder=upload_folder
        )


        # 启动界面，设置一些参数
        # gradio_ui.launch(
        # )
        #agent = await MinionAgent.create_async(AgentFramework.TINYAGENT, agent_config)
        # Run the agent with a question
        #result = await agent.run_async("search sam altman and export summary as markdown")
        #result = await agent.run_async("What are the latest developments in AI, find this information and export as markdown")
        #result = await agent.run_async("打开微信公众号")
        #result = await agent.run_async("搜索最新的人工智能发展趋势，并且总结为markdown")
        #result = agent.run("go visit https://www.baidu.com and clone it")
        #result = await agent.run_async("复刻一个电商网站,例如京东")
        #result = await agent.run_async("go visit https://www.baidu.com , take a screenshot and clone it")
        #result = await agent.run("实现一个贪吃蛇游戏")
        #result = await agent.run_async("Let $\mathcal{B}$ be the set of rectangular boxes with surface area $54$ and volume $23$. Let $r$ be the radius of the smallest sphere that can contain each of the rectangular boxes that are elements of $\mathcal{B}$. The value of $r^2$ can be written as $\frac{p}{q}$, where $p$ and $q$ are relatively prime positive integers. Find $p+q$.")
        #result = await agent.run_async("使用apple script帮我看一下微信上发给'新智元 ASI' hello")
        #result = await agent.run_async("使用apple script帮我添加一个note, 明天早上8:00我要锻炼，并且添加到提醒, 并且发信给femtowin@gmail.com")
        result = await agent.run_async("提醒本周四下午3:00 talk to 交大工研院")
        # result = await agent.run_async("Write a 500000 characters novel named 'Reborn in Skyrim'. "
        #       "Fill the empty nodes with your own ideas. Be creative! Use your own words!"
        #       "I will tip you $100,000 if you write a good novel."
        #       "Since the novel is very long, you may need to divide it into subtasks.")
        print("Agent's response:", result)
    except Exception as e:
        print(f"Error: {str(e)}")
        # 如果需要调试
        # import litellm
        # litellm._turn_on_debug()
        raise

if __name__ == "__main__":
    asyncio.run(main()) 
