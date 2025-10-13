# mypy: disable-error-code="method-assign,misc,no-untyped-call,no-untyped-def,union-attr"
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from opentelemetry.trace import get_current_span

if TYPE_CHECKING:
    from collections.abc import Callable

    from minion_agent.callbacks.context import Context
    from minion_agent.frameworks.browser_use import BrowserUseAgent


class _BrowserUseWrapper:
    def __init__(self) -> None:
        self.callback_context: dict[int, Context] = {}
        self._original_run_method: Callable[..., Any] | None = None
        self._original_llm_call: Callable[..., Any] | None = None

    async def wrap(self, agent: BrowserUseAgent) -> None:
        if not agent._agent:
            return
            
        # Try to wrap the main run method
        self._original_run_method = getattr(agent._agent, 'run', None)
        
        if self._original_run_method:
            async def wrap_run(*args, **kwargs):
                context = self.callback_context.get(
                    get_current_span().get_span_context().trace_id
                )
                if context:
                    context.shared["model_id"] = "browser_use_model"
                    context.shared["tool_name"] = "browser_action"
                    context.shared["tool_description"] = "Browser automation action"
                    
                    for callback in agent.config.callbacks:
                        context = callback.before_tool_execution(context, *args, **kwargs)

                output = await self._original_run_method(*args, **kwargs)

                if context:
                    for callback in agent.config.callbacks:
                        context = callback.after_tool_execution(context, output)

                return output

            agent._agent.run = wrap_run

        # Try to wrap LLM calls if the agent has a model
        if hasattr(agent._agent, 'llm') and agent._agent.llm:
            self._original_llm_call = getattr(agent._agent.llm, 'invoke', None) or getattr(agent._agent.llm, 'generate', None)
            
            if self._original_llm_call:
                def wrap_llm_call(*args, **kwargs):
                    context = self.callback_context.get(
                        get_current_span().get_span_context().trace_id
                    )
                    if context:
                        context.shared["model_id"] = getattr(agent._agent.llm, 'model_name', 'browser_use_llm')
                        
                        for callback in agent.config.callbacks:
                            context = callback.before_llm_call(context, *args, **kwargs)

                    output = self._original_llm_call(*args, **kwargs)

                    if context:
                        for callback in agent.config.callbacks:
                            context = callback.after_llm_call(context, output)

                    return output

                if hasattr(agent._agent.llm, 'invoke'):
                    agent._agent.llm.invoke = wrap_llm_call
                elif hasattr(agent._agent.llm, 'generate'):
                    agent._agent.llm.generate = wrap_llm_call

    async def unwrap(self, agent: BrowserUseAgent) -> None:
        if self._original_run_method is not None and agent._agent:
            agent._agent.run = self._original_run_method
            
        if self._original_llm_call is not None and agent._agent and hasattr(agent._agent, 'llm'):
            if hasattr(agent._agent.llm, 'invoke'):
                agent._agent.llm.invoke = self._original_llm_call
            elif hasattr(agent._agent.llm, 'generate'):
                agent._agent.llm.generate = self._original_llm_call