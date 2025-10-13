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

DEFAULT_AGENT_TYPE = Brain
DEFAULT_MODEL_TYPE = "gpt-4o"


class SurrogateModel:
    """Surrogate model class for external minion agent.
    
    This is a placeholder model class that doesn't actually implement any LLM functionality.
    The real model is created and managed by the external minion framework.
    """
    
    def __init__(self, *args, **kwargs):
        # Accept any arguments but don't do anything with them
        # The real model configuration is handled by _get_model method
        pass
    
    def __call__(self, *args, **kwargs):
        raise NotImplementedError("SurrogateModel is a placeholder. Real model is handled by external minion framework.")
    
    def complete(self, *args, **kwargs):
        raise NotImplementedError("SurrogateModel is a placeholder. Real model is handled by external minion framework.")


class ExternalMinionAgent(MinionAgent):
    """External minion framework agent implementation using code_agent or tool_calling_agent."""

    def __init__(
        self,
        config: AgentConfig,
        managed_agents: list[AgentConfig] | None = None,
    ):
        super().__init__(config, managed_agents)
        self._agent: Any = None

    @property
    def framework(self) -> AgentFramework:
        return AgentFramework.EXTERNAL_MINION_AGENT

    def _get_model(self, agent_config: AgentConfig) -> Any:
        """Get the model configuration for an external minion agent."""
        # Reference implementation: llm_config = config.models.get(model)
        # llm = create_llm_provider(llm_config)
        # we don't use agent_config.model_type (SurrogateModel)
        model_args = agent_config.model_args or {}
        # Use model from model_args first, then model_id, then default
        model = model_args.get("model") or agent_config.model_id or "gpt-4o-mini"
        
        # Try to get model config from minion's config first
        try:
            llm_config = minion_config.models.get(model)
        except:
            llm_config = None
            
        if not llm_config:
            # Create a custom config using agent_config model_args
            llm_config = {
                "provider": "azure_openai",
                "model": model,
                "azure_endpoint": model_args.get("azure_endpoint"),
                "api_key": model_args.get("api_key") or agent_config.api_key,
                "api_version": model_args.get("api_version", "2024-02-15-preview"),
            }
            # Add other model_args but avoid duplicating the above keys
            for key, value in model_args.items():
                if key not in ["model", "azure_endpoint", "api_key", "api_version"]:
                    llm_config[key] = value
        
        return create_llm_provider(llm_config)

    async def _load_agent(self) -> None:
        """Load external minion framework agent (code_agent or tool_calling_agent)."""
        if not minion_available:
            msg = "You need to install the external minion framework to use this agent"
            raise ImportError(msg)

        tools, _ = await self._load_tools(self.config.tools or [])

        #todo, support managed_agents
        managed_agents_instanced = []
        if self.managed_agents:
            for managed_agent in self.managed_agents:
                agent_type = managed_agent.agent_type or DEFAULT_AGENT_TYPE
                managed_tools, _ = await self._load_tools(managed_agent.tools)
                managed_agent_instance = agent_type(
                    name=managed_agent.name,
                    model=self._get_model(managed_agent),
                    tools=managed_tools,
                    verbosity_level=2,
                    description=managed_agent.description
                                or f"Use the agent: {managed_agent.name}",
                )
                if managed_agent.instructions:
                    managed_agent_instance.prompt_templates["system_prompt"] = (
                        managed_agent.instructions
                    )
                managed_agents_instanced.append(managed_agent_instance)

        # Get agent type from config, default to code_agent
        agent_args = self.config.agent_args or {}
        agent_type = self.config.agent_type or ExternalCodeAgent
        
        # Get model configuration
        llm_provider = self._get_model(self.config)
        
        self._main_agent_tools = tools

        self._agent = agent_type(
            llm=llm_provider,
            tools = tools,
            **agent_args
        )

        # Call setup() method if it exists (required by external minion framework)
        if hasattr(self._agent, 'setup'):
            # Try async setup first, then sync if that fails
            try:
                await self._agent.setup()
            except TypeError:
                # If setup is not async, call it synchronously
                self._agent.setup()

        assert self._agent

    async def _run_async(self, prompt: str, **kwargs: Any) -> str:
        if not self._agent:
            error_message = "Agent not loaded. Call load_agent() first."
            raise ValueError(error_message)
        
        result = await self._agent.run_async(task=prompt, **kwargs)
        return result
