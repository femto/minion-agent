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

def parse_tool_args_if_needed(message: ChatMessage) -> ChatMessage:
    for tool_call in message.tool_calls:
        tool_call.function.arguments = parse_json_if_needed(tool_call.function.arguments)
    return message

from minion_agent.config import MCPStdio

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
        MCPStdio(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem","/Users/femtozheng/workspace","/Users/femtozheng/python-project/minion-agent"]
        )
    ],
    agent_type=CodeAgent,
    model_type=AzureOpenAIServerModel,  # Updated to use our custom model
    #model_type=CustomAzureOpenAIServerModel,  # Updated to use our custom model
    agent_args={
        #"additional_authorized_imports":"*",
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
        agent = await MinionAgent.create_async(AgentFramework.MINION, agent_config)
        # Run the agent with a question
        result = await agent.run_async("what's the solution for game of 24 for 2,4,5,8", check=False)
        print("Agent's response:", result)
    except Exception as e:
        print(f"Error: {str(e)}")
        # 如果需要调试
        # import litellm
        # litellm._turn_on_debug()
        raise

if __name__ == "__main__":
    asyncio.run(main()) 
