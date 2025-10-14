import os
import importlib
from typing import Optional, Any, List

from pydantic import SecretStr

from minion_agent.config import AgentFramework, AgentConfig
from minion_agent.frameworks.minion_agent import MinionAgent

try:
    import browser_use
    from browser_use import Agent
    from browser_use import Agent, Browser,  ChatOpenAI

    browser_use_available = True
except ImportError:
    browser_use_available = None

DEFAULT_MODEL_CLASS = ChatOpenAI

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

        model_type = agent_config.model_type or DEFAULT_MODEL_CLASS
        model_args = agent_config.model_args or {}
        kwargs = {
            "model": agent_config.model_id,
        }
        return model_type(**kwargs)

    async def _load_agent(self) -> None:
        """Load the Browser-use agent with the given configuration."""
        if not self.config.tools:
            self.config.tools = []  # Browser-use has built-in browser automation tools

        tools, mcp_clients = await self._load_tools(
            self.config.tools or []
        )
        self._mcp_servers = mcp_clients

        self._agent = Agent(
            task=self.config.instructions or "No specific task provided",
            llm=self._get_model(self.config),
            **self.config.agent_args or {},
        )

    async def _run_async(self, prompt: str) -> Any:
        """Run the Browser-use agent with the given prompt."""
        # Update the agent's task with the new prompt
        self._agent.task = prompt
        self._agent._message_manager.task = prompt
        #self._agent._message_manager.state.history
        result = await self._agent.run()
        return result

    @property
    def tools(self) -> List[str]:
        """
        Return the tools used by the agent.
        This property is read-only and cannot be modified.
        """
        return []  # Browser-use has built-in browser tools
