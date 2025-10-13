# mypy: disable-error-code="method-assign,misc,no-untyped-call,no-untyped-def,union-attr"
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from opentelemetry.trace import get_current_span

if TYPE_CHECKING:
    from collections.abc import Callable

    from minion_agent.callbacks.context import Context
    from minion_agent.frameworks.deep_research import DeepResearchAgent


class _DeepResearchWrapper:
    def __init__(self) -> None:
        self.callback_context: dict[int, Context] = {}
        self._original_research_method: Callable[..., Any] | None = None

    async def wrap(self, agent: DeepResearchAgent) -> None:
        if not agent._agent:
            return
            
        # Store original research method
        self._original_research_method = getattr(agent._agent, 'research_topic', None)
        
        if self._original_research_method:
            async def wrap_research_topic(*args, **kwargs):
                context = self.callback_context.get(
                    get_current_span().get_span_context().trace_id
                )
                if context:
                    context.shared["model_id"] = "deep_research_model"
                    
                    for callback in agent.config.callbacks:
                        context = callback.before_llm_call(context, *args, **kwargs)

                output = await self._original_research_method(*args, **kwargs)

                if context:
                    for callback in agent.config.callbacks:
                        context = callback.after_llm_call(context, output)

                return output

            agent._agent.research_topic = wrap_research_topic

    async def unwrap(self, agent: DeepResearchAgent) -> None:
        if self._original_research_method is not None and agent._agent:
            agent._agent.research_topic = self._original_research_method