**[![Documentation Status](https://img.shields.io/badge/documentation-brightgreen)](https://github.com/femto/minion-agent) 
[![Install](https://img.shields.io/badge/get_started-blue)](https://github.com/femto/minion-agent) 
[![Discord](https://dcbadge.limes.pink/api/server/HUC6xEK9aT?style=flat)](https://discord.gg/HUC6xEK9aT)
[![Twitter Follow](https://img.shields.io/twitter/follow/femtowin?style=social)](https://x.com/femtowin)**
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/femto/minion-agent)
# Minion Agent

A powerful agent framework with enhanced capabilities including browser automation, code execution, MCP tool support, and deep research. **Now defaults to EXTERNAL_MINION_AGENT framework** for superior performance and functionality.

## 🎬 Demo Videos

- [Compare Price Demo](https://youtu.be/O0RhA3eeDlg)
- [Deep Research Demo](https://youtu.be/tOd56nagsT4)
- [Generating Snake Game Demo](https://youtu.be/UBquRXD9ZJc)

## Quick Start

Minion Agent now defaults to the powerful `EXTERNAL_MINION_AGENT` framework, providing enhanced code execution, browser automation, and advanced planning capabilities out of the box.

## Installation

```bash
pip install minion-agent-x
```
## Or from source
```bash
git clone git@github.com:femto/minion-agent.git
cd minion-agent
pip install -e .
```

## Usage

Here's a simple example of how to use Minion Agent:

```python
import asyncio
import os
from dotenv import load_dotenv
from minion_agent import MinionAgent, AgentConfig, AgentFramework
from minion.agents import CodeAgent
import minion_agent

load_dotenv()

async def main():
    # Configure the agent (using EXTERNAL_MINION_AGENT as default)
    agent_config = AgentConfig(
        model_id=os.environ.get("AZURE_DEPLOYMENT_NAME"),
        name="research_assistant",
        description="A helpful research assistant",
        model_args={
            "azure_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT"),
            "api_key": os.environ.get("AZURE_OPENAI_API_KEY"),
            "api_version": os.environ.get("OPENAI_API_VERSION"),
            "model": "gpt-4o",  # Actual model to use in minion framework
        },
        tools=[
            minion_agent.tools.browser_tool.browser,
        ],
        agent_type=CodeAgent,  # Default agent type for EXTERNAL_MINION_AGENT
    )

    # Create agent with EXTERNAL_MINION_AGENT framework (default)
    agent = await MinionAgent.create_async(AgentFramework.EXTERNAL_MINION_AGENT, agent_config)

    # Run the agent with a question
    result = await agent.run_async("What are the latest developments in AI?")
    print("Agent's response:", result.final_output.content)

if __name__ == "__main__":
    asyncio.run(main())
```

see example.py
see example_browser_use.py
see example_with_managed_agents.py
see example_deep_research.py
see example_reason.py

## Agent Frameworks

Minion Agent supports multiple agent frameworks. The default framework is `EXTERNAL_MINION_AGENT`, which provides enhanced capabilities including:

- **Code Generation and Execution**: Advanced code generation with built-in execution capabilities
- **Browser Automation**: Integrated browser control and web interaction
- **MCP Tool Support**: Full Model Context Protocol integration
- **Enhanced Planning**: Sophisticated task planning and execution

### Available Frameworks

- `EXTERNAL_MINION_AGENT` (Default): Enhanced framework with code execution and browser capabilities
- `SMOLAGENTS`: HuggingFace's smolagents framework with planning support
- `LANGCHAIN`: LangChain-based agents
- `OPENAI`: OpenAI's assistant API
- `BROWSER_USE`: Specialized for browser automation tasks
- `DEEP_RESEARCH`: Optimized for research and information gathering

### Framework-Specific Agent Types

When using `EXTERNAL_MINION_AGENT`, you can specify different agent types:

```python
from minion.agents import CodeAgent, ToolCallingAgent

agent_config = AgentConfig(
    # ... other config ...
    agent_type=CodeAgent,  # For code generation and execution
    # or
    # agent_type=ToolCallingAgent,  # For general tool calling
)
```

## Configuration

The `AgentConfig` class accepts the following parameters:

- `model_id`: The ID of the model to use (e.g., "gpt-4")
- `name`: Name of the agent (default: "Minion")
- `description`: Optional description of the agent
- `instructions`: Optional system instructions for the agent
- `tools`: List of tools the agent can use
- `model_type`: model type of the underlying agent framework
- `model_args`: Optional dictionary of model-specific arguments
- `agent_type`: agent type of the underlying agent framework
- `agent_args`: Optional dictionary of agent-specific arguments

## MCP Tool Support

Minion Agent supports Model Context Protocol (MCP) tools. Here's how to use them:

### Standard MCP Tool

```python
from minion_agent.config import MCPTool

agent_config = AgentConfig(
    # ... other config options ...
    tools=[
        minion_agent.tools.browser_tool.browser,  # Regular tools
        MCPTool(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/path/to/workspace"]
        )  # MCP tool
    ]
)
```

### SSE-based MCP Tool

You can also use MCP tools over Server-Sent Events (SSE). This is useful for connecting to remote MCP servers:

```python
from minion_agent.config import MCPTool

agent_config = AgentConfig(
    # ... other config options ...
    tools=[
        MCPTool({"url": "http://localhost:8000/sse"}),  # SSE-based tool
    ]
)
```

⚠️ **Security Warning**: When using MCP servers over SSE, be extremely cautious and only connect to trusted and verified servers. Always verify the source and security of any MCP server before connecting.

You can also use multiple MCP tools together:

```python
tools=[
    MCPTool(command="npx", args=["..."]),  # Standard MCP tool
    MCPTool({"url": "http://localhost:8000/sse"}),  # SSE-based tool
    MCPTool({"url": "http://localhost:8001/sse"})   # Another SSE-based tool
]
```

## Planning Support in smolagents

You can enable automatic planning by setting the `planning_interval` in `agent_args` (smolagents) :

```python
agent_config = AgentConfig(
    # ... other config options ...
    agent_args={
        "planning_interval": 3,  # Agent will create a plan every 3 steps
        "additional_authorized_imports": "*"
    }
)
```

The `planning_interval` parameter determines how often the agent should create a new plan. When set to 3, the agent will:
1. Create an initial plan for the task
2. Execute 3 steps according to the plan
3. Re-evaluate and create a new plan based on progress
4. Repeat until the task is complete

## Environment Variables

Make sure to set up your environment variables in a `.env` file:

```env
# For Azure OpenAI (recommended for EXTERNAL_MINION_AGENT)
AZURE_DEPLOYMENT_NAME=your_deployment_name
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_azure_api_key
OPENAI_API_VERSION=2024-02-15-preview

# Or for OpenAI
OPENAI_API_KEY=your_openai_api_key

# Optional: For other providers via LiteLLM
# ANTHROPIC_API_KEY=your_anthropic_key
# GOOGLE_API_KEY=your_google_key
```

## Development

To set up for development:

```bash
# Clone the repository
git clone https://github.com/yourusername/minion-agent.git
cd minion-agent

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
```

## Deep Research

See [Deep Research Documentation](docs/deep_research.md) for usage instructions.

## Community

Join our WeChat discussion group to connect with other users and get help:

![WeChat Discussion Group](docs/images/wechat_group_qr.png)

群聊: minion-agent讨论群

## License

MIT License


