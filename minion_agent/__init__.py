from importlib.metadata import PackageNotFoundError, version

from .config import AgentConfig, AgentFramework
from .frameworks.minion_agent import AgentRunError, MinionAgent
from .tracing.agent_trace import AgentTrace

try:
    __version__ = version("minion-agent-x")
except PackageNotFoundError:
    # In the case of local development
    # i.e., running directly from the source directory without package being installed
    __version__ = "0.0.0-dev"

__all__ = [
    "AgentConfig",
    "AgentFramework",
    "AgentRunError",
    "AgentTrace",
    "MinionAgent",
    "__version__",
]
