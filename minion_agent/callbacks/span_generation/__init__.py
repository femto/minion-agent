from __future__ import annotations

from typing import assert_never

from minion_agent import AgentFramework

from .agno import _AgnoSpanGeneration
from .google import _GoogleSpanGeneration
from .langchain import _LangchainSpanGeneration
from .llama_index import _LlamaIndexSpanGeneration
from .openai import _OpenAIAgentsSpanGeneration
from .smolagents import _SmolagentsSpanGeneration
from .tinyagent import _TinyAgentSpanGeneration
from .minion import _ExternalMinionAgentSpanGeneration

SpanGeneration = (
    _AgnoSpanGeneration
    | _GoogleSpanGeneration
    | _LangchainSpanGeneration
    | _LlamaIndexSpanGeneration
    | _OpenAIAgentsSpanGeneration
    | _SmolagentsSpanGeneration
    | _TinyAgentSpanGeneration
    | _ExternalMinionAgentSpanGeneration
)


def _get_span_generation_callback(
    framework: AgentFramework,
) -> SpanGeneration:
    if framework is AgentFramework.AGNO:
        return _AgnoSpanGeneration()

    if framework is AgentFramework.GOOGLE:
        return _GoogleSpanGeneration()

    if framework is AgentFramework.LANGCHAIN:
        return _LangchainSpanGeneration()

    if framework is AgentFramework.LLAMA_INDEX:
        return _LlamaIndexSpanGeneration()

    if framework is AgentFramework.OPENAI:
        return _OpenAIAgentsSpanGeneration()

    if framework is AgentFramework.SMOLAGENTS:
        return _SmolagentsSpanGeneration()

    if framework is AgentFramework.TINYAGENT:
        return _TinyAgentSpanGeneration()
    if framework is AgentFramework.EXTERNAL_MINION_AGENT:
        return _ExternalMinionAgentSpanGeneration()

    assert_never(framework)
