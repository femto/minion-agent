import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from minion_agent.config import AgentConfig, AgentFramework, TracingConfig
from minion_agent.frameworks.minion_agent import MinionAgent

# Add external minion framework path
EXTERNAL_MINION_PATH = "/Users/femtozheng/python-project/minion1"
if EXTERNAL_MINION_PATH not in sys.path:
    sys.path.insert(0, EXTERNAL_MINION_PATH)

try:
    from minion.main.brain import Brain
    from minion.providers import create_llm_provider
    from minion import config as minion_config
    from minion.main.local_python_env import LocalPythonEnv
    # Import external agents
    from minion.agents.code_agent import CodeAgent as ExternalCodeAgent
    from minion.agents.tool_calling_agent import ToolCallingAgent as ExternalToolCallingAgent
    minion_available = True
except ImportError as e:
    minion_available = False
    print(f"Warning: External minion framework not available: {e}")

if TYPE_CHECKING:
    from minion.main.brain import Brain as MinionBrain

DEFAULT_AGENT_TYPE = ExternalCodeAgent
DEFAULT_MODEL_TYPE = "gpt-4o"

class ExternalMinionAgent(MinionAgent):
    """External minion framework agent implementation using code_agent or tool_calling_agent."""

    def __init__(
        self,
        config: AgentConfig,
        managed_agents: list[AgentConfig] | None = None,
        tracing: TracingConfig | None = None,
    ):
        super().__init__(config, managed_agents, tracing)
        self._agent: Any = None

    @property
    def framework(self) -> AgentFramework:
        return AgentFramework.MINION

    def _get_model(self, agent_config: AgentConfig) -> Any:
        """Get the model configuration for an external minion agent."""
        model_id = agent_config.model_id or DEFAULT_MODEL_TYPE
        
        # Try to get model config from minion's config first
        try:
            llm_config = minion_config.models.get(model_id)
        except:
            llm_config = None
            
        if not llm_config:
            # Create a custom config using agent_config model_args
            model_args = agent_config.model_args or {}
            llm_config = {
                "provider": "azure_openai",
                "model": model_id,
                "azure_endpoint": model_args.get("azure_endpoint"),
                "api_key": model_args.get("api_key") or agent_config.api_key,
                "api_version": model_args.get("api_version", "2024-02-15-preview"),
            }
            # Add other model_args but avoid duplicating the above keys
            for key, value in model_args.items():
                if key not in ["azure_endpoint", "api_key", "api_version"]:
                    llm_config[key] = value
        
        return create_llm_provider(llm_config)

    async def _load_agent(self) -> None:
        """Load external minion framework agent (code_agent or tool_calling_agent)."""
        if not minion_available:
            msg = "You need to install the external minion framework to use this agent"
            raise ImportError(msg)

        tools, _ = await self._load_tools(self.config.tools or [])

        # Get agent type from config, default to code_agent
        agent_args = self.config.agent_args or {}
        agent_type = agent_args.pop('agent_type', 'code')
        
        # Get model configuration
        llm_provider = self._get_model(self.config)
        
        self._main_agent_tools = tools
        
        if agent_type == 'code':
            # Create Python environment for code agent
            python_env = agent_args.pop('python_env', None) or LocalPythonEnv(verbose=False)
            self._agent = ExternalCodeAgent(
                llm=llm_provider,
                python_env=python_env,
                **agent_args
            )
        elif agent_type == 'tool_calling':
            self._agent = ExternalToolCallingAgent(
                llm=llm_provider,
                **agent_args
            )
        else:
            raise ValueError(f"Unsupported external agent type: {agent_type}. Use 'code' or 'tool_calling'.")

        assert self._agent

    async def _run_async(self, prompt: str, **kwargs: Any) -> str:
        if not self._agent:
            error_message = "Agent not loaded. Call load_agent() first."
            raise ValueError(error_message)
        
        result = await self._agent.step(query=prompt, **kwargs)
        # Extract the observation from the result tuple
        if isinstance(result, tuple) and len(result) > 0:
            return str(result[0])
        return str(result)
