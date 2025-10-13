# mypy: disable-error-code="no-untyped-def,union-attr"
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from minion_agent.callbacks.span_generation.base import _SpanGeneration

if TYPE_CHECKING:
    from minion_agent.callbacks.context import Context


class _BrowserUseSpanGeneration(_SpanGeneration):
    def before_llm_call(self, context: Context, *args, **kwargs) -> Context:
        model_id = context.shared.get("model_id", "unknown")
        
        # Extract messages from args if available
        input_messages = []
        if args and len(args) > 0:
            messages = args[0]
            if isinstance(messages, list):
                for message in messages:
                    if isinstance(message, dict):
                        input_messages.append({
                            "role": message.get("role", "user"),
                            "content": str(message.get("content", ""))
                        })
                    elif hasattr(message, 'role') and hasattr(message, 'content'):
                        input_messages.append({
                            "role": str(message.role),
                            "content": str(message.content)
                        })
            elif isinstance(messages, str):
                input_messages = [{"role": "user", "content": messages}]

        return self._set_llm_input(context, model_id, input_messages)

    def after_llm_call(self, context: Context, *args, **kwargs) -> Context:
        output = ""
        input_tokens = 0
        output_tokens = 0
        
        if args and len(args) > 0:
            response = args[0]
            if isinstance(response, str):
                output = response
            elif hasattr(response, 'content'):
                output = str(response.content)
            elif isinstance(response, dict):
                output = response.get('content', str(response))
            else:
                output = str(response)
                
            # Try to extract token usage if available
            if hasattr(response, 'usage'):
                usage = response.usage
                if hasattr(usage, 'prompt_tokens'):
                    input_tokens = usage.prompt_tokens
                if hasattr(usage, 'completion_tokens'):
                    output_tokens = usage.completion_tokens

        return self._set_llm_output(context, output, input_tokens, output_tokens)

    def before_tool_execution(self, context: Context, *args, **kwargs) -> Context:
        tool_name = context.shared.get("tool_name", "browser_action")
        tool_description = context.shared.get("tool_description", "Browser automation action")
        
        return self._set_tool_input(
            context, 
            name=tool_name, 
            description=tool_description, 
            args=kwargs
        )

    def after_tool_execution(self, context: Context, *args, **kwargs) -> Context:
        tool_output = args[0] if args else None
        return self._set_tool_output(context, tool_output)