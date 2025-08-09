"""Example usage of Minion Agent."""

import asyncio
from dotenv import load_dotenv
import os
from PIL import Image
from io import BytesIO
from time import sleep
from typing import List, Dict, Optional
from smolagents import (Tool, ChatMessage)
from smolagents.models import parse_json_if_needed
from custom_azure_model import CustomAzureOpenAIServerModel
from minion_agent.config import MCPStdio
from smolagents import CodeAgent, ToolCallingAgent, AzureOpenAIServerModel
import minion_agent

def parse_tool_args_if_needed(message: ChatMessage) -> ChatMessage:
    for tool_call in message.tool_calls:
        tool_call.function.arguments = parse_json_if_needed(tool_call.function.arguments)
    return message

from minion_agent import MinionAgent, AgentConfig, AgentFramework

from smolagents import (
    DuckDuckGoSearchTool,
    VisitWebpageTool,
    ActionStep,
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
        minion_agent.tools.browser_tool.browser,
        minion_agent.tools.generation.generate_pdf,
        minion_agent.tools.generation.generate_html,
        minion_agent.tools.generation.save_and_generate_html,
        MCPStdio(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem","/Users/femtozheng/workspace","/Users/femtozheng/python-project/minion-agent"]
        ),
    ],
    agent_type=CodeAgent,
    model_type=AzureOpenAIServerModel,  # Updated to use our custom model
    #model_type=CustomAzureOpenAIServerModel,  # Updated to use our custom model
    agent_args={"additional_authorized_imports":"*",
                #"planning_interval":3
#"step_callbacks":[save_screenshot]
                }
)
managed_agents = [
    AgentConfig(
        name="search_web_agent",
        model_id="gpt-4o-mini",
        description="Agent that can use the browser, search the web,navigate",
        tools=[minion_agent.tools.browser_tool.browser],
        model_args={"azure_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT"),
                "api_key": os.environ.get("AZURE_OPENAI_API_KEY"),
                "api_version": os.environ.get("OPENAI_API_VERSION"),
                },
        model_type=AzureOpenAIServerModel,  # Updated to use our custom model
        #model_type=CustomAzureOpenAIServerModel,  # Updated to use our custom model
        agent_type=ToolCallingAgent,
        agent_args={
            #"additional_authorized_imports":"*",
                    #"planning_interval":3

                    }
    ),
    # AgentConfig(
    #     name="visit_webpage_agent",
    #     model_id="gpt-4o-mini",
    #     description="Agent that can visit webpages",
    #     tools=["minion_agent.tools.web_browsing.visit_webpage"]
    # )
]

from opentelemetry.sdk.trace import TracerProvider

from openinference.instrumentation.smolagents import SmolagentsInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
trace_provider = TracerProvider()
trace_provider.add_span_processor(SimpleSpanProcessor(otlp_exporter))

SmolagentsInstrumentor().instrument(tracer_provider=trace_provider)

async def main():
    try:
        # Create and run the agent
        agent = await MinionAgent.create_async(AgentFramework.SMOLAGENTS, agent_config)
        # Run the agent with a question
        result = await agent.run_async("搜索Deepseek prover的最新消息，汇总成一个html, 你的html应该尽可能美观,然后保存html到磁盘上")
        print("Agent's response:", result)
        print("done")
    except Exception as e:
        print(f"Error: {str(e)}")
        # 如果需要调试
        # import litellm
        # litellm._turn_on_debug()
        raise

if __name__ == "__main__":
    asyncio.run(main()) 
