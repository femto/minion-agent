import os
import importlib
from typing import Optional, Any, List

from pydantic import SecretStr

from minion_agent.config import AgentFramework, AgentConfig
from minion_agent.frameworks.minion_agent import MinionAgent
from minion_agent.tools.wrappers import import_and_wrap_tools

try:
    import browser_use
    from browser_use import Agent
    from browser_use import Agent, Browser, BrowserConfig

    browser_use_available = True
except ImportError:
    browser_use_available = None

DEFAULT_MODEL_CLASS = "langchain_openai.ChatOpenAI"

class BrowserUseAgent(MinionAgent):
    """Browser-use agent implementation that handles both loading and running."""
    name = "browser_agent"
    description = "Browser-use agent"

    def __init__(
        self, config: AgentConfig, managed_agents: Optional[list[AgentConfig]] = None
    ):
        super().__init__(config, managed_agents)
        if not browser_use_available:
            raise ImportError(
                "You need to `pip install 'minion-agent-x[browser_use]'` to use this agent"
            )
        self.managed_agents = managed_agents
        self.config = config
        self._agent = None
        self._agent_loaded = False
        self._mcp_servers = None

    @property
    def framework(self) -> AgentFramework:
        return AgentFramework.BROWSER_USE

    def _get_model(self, agent_config: AgentConfig):
        """Get the model configuration for a LangChain agent."""
        if not agent_config.model_type:
            agent_config.model_type = DEFAULT_MODEL_CLASS
        module, class_name = agent_config.model_type.split(".")
        model_type = getattr(importlib.import_module(module), class_name)

        return model_type(model=agent_config.model_id, **agent_config.model_args or {})

    async def _load_agent(self) -> None:
        """Load the Browser-use agent with the given configuration."""
        if not self.config.tools:
            self.config.tools = []  # Browser-use has built-in browser automation tools

        tools, mcp_servers = await import_and_wrap_tools(
            self.config.tools, agent_framework=AgentFramework.BROWSER_USE
        )
        self._mcp_servers = mcp_servers

        # Initialize the browser-use Agent
        browser = Browser(
            config=BrowserConfig(
                # Specify the path to your Chrome executable
                #browser_binary_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',  # macOS path
                # For Windows, typically: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
                # For Linux, typically: '/usr/bin/google-chrome'
            )
        )

        self._agent = Agent(
            task=self.config.instructions or "No specific task provided",
            llm=self._get_model(self.config),
            browser = browser,
        )

    async def _run_async(self, prompt: str) -> Any:
        """Run the Browser-use agent with the given prompt."""
        # Update the agent's task with the new prompt
        self._agent.task = prompt
        self._agent._message_manager.task = prompt
        self._agent._message_manager.state.history.messages[1].message.content = f'Your ultimate task is: """{prompt}""". If you achieved your ultimate task, stop everything and use the done action in the next step to complete the task. If not, continue as usual.'
        result = await self._agent.run()
        return result

    @property
    def tools(self) -> List[str]:
        """
        Return the tools used by the agent.
        This property is read-only and cannot be modified.
        """
        return []  # Browser-use has built-in browser tools
