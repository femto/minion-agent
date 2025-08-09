"""Example usage of Minion Agent with Apple Script tools."""

import asyncio
import logging

from dotenv import load_dotenv
import os
from PIL import Image
from io import BytesIO
from time import sleep
from typing import List, Dict, Optional
from smolagents import (Tool, ChatMessage)
from smolagents.models import parse_json_if_needed
from custom_azure_model import CustomAzureOpenAIServerModel
import minion_agent
from minion_agent.config import MCPStdio, MCPSse
from minion_agent.logging import setup_logger
from minion_agent.tools.run_apple_script import run_applescript, run_applescript_capture, run_command

# Import Apple Script tools
from minion_agent.tools.apple_script_tools import (
    create_calendar_event,
    create_reminder, 
    create_note,
    compose_email,
    send_sms,
    get_contact_phone,
    get_contact_email,
    open_location_maps,
    get_directions_maps,
    spotlight_search_open
)


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
    HfApiModel, AzureOpenAIServerModel, ActionStep,
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
    description="A helpful research assistant with Apple Script capabilities",
    model_args={"azure_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT"),
                "api_key": os.environ.get("AZURE_OPENAI_API_KEY"),
                "api_version": os.environ.get("OPENAI_API_VERSION"),
                },
    tools=[
        # Basic Apple Script tools
        run_applescript, run_applescript_capture, run_command,
        
        # Apple Script wrapper tools
        create_calendar_event,
        create_reminder, 
        create_note,
        compose_email,
        send_sms,
        get_contact_phone,
        get_contact_email,
        open_location_maps,
        get_directions_maps,
        spotlight_search_open,
        
        # MCP tools
        MCPStdio(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem","/Users/femtozheng/workspace","/Users/femtozheng/python-project/minion-agent"]
        ),
    ],
    model_type=AzureOpenAIServerModel,
    agent_type=CodeAgent,
    agent_args={"additional_authorized_imports":"*"}
)
# setup_logger(logging.DEBUG)
async def main():
    try:
        # Create and run the agent
        agent = await MinionAgent.create_async(AgentFramework.SMOLAGENTS, agent_config)
        #agent = await MinionAgent.create_async(AgentFramework.TINYAGENT, agent_config)

        # Test various Apple Script functionalities
        
        # Example 1: Create a reminder
        # result = await agent.run_async("提醒今晚9:15鼠标要充电")
        
        # Example 2: Create a note and reminder
        # result = await agent.run_async("添加一个note, 明天早上8:00我要锻炼，并且添加到提醒")
        
        # Example 3: Send email
        # result = await agent.run_async("发信给femtowin@gmail.com, 主题是测试邮件, 内容是这是一个测试邮件")
        
        # Example 4: Multiple tasks
        result = await agent.run_async("帮我做以下几件事：1. 添加一个提醒明天下午3点开会 2. 创建一个笔记记录今天的工作内容 3. 查看我的联系人中是否有femto的信息")
        
        print("Agent's response:", result)
    except Exception as e:
        print(f"Error: {str(e)}")
        # 如果需要调试
        # import litellm
        # litellm._turn_on_debug()
        raise

if __name__ == "__main__":
    asyncio.run(main()) 
