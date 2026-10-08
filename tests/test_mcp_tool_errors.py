"""MCP tool failures are returned as "Error: MCP tool <name> failed: ..." strings."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("mcp")

from mcp.types import Tool

from minion_agent.config import AgentFramework, MCPStreamableHttp
from minion_agent.tools.mcp.mcp_client import MCPClient, call_tool_error_text


def text(value):
    return SimpleNamespace(type="text", text=value)


def make_tool(call_tool_result=None, side_effect=None):
    client = MCPClient(
        config=MCPStreamableHttp(url="http://localhost/mcp"),
        framework=AgentFramework.EXTERNAL_MINION_AGENT,
    )
    client._session = AsyncMock()
    client._session.call_tool.return_value = call_tool_result
    client._session.call_tool.side_effect = side_effect
    return client._create_tool_function(Tool(name="web_search", inputSchema={"type": "object"}))


@pytest.mark.parametrize("flag", ["isError", "is_error"])  # MCP 1.x / 2.x spelling
async def test_is_error_result_is_reported(flag):
    result = SimpleNamespace(content=[text("Request limit reached"), text("Try again later")], **{flag: True})
    assert await make_tool(result)() == (
        "Error: MCP tool web_search failed: Request limit reached\nTry again later"
    )


async def test_error_text_takes_precedence_over_structured_content():
    result = SimpleNamespace(isError=True, content=[text("bad input")], structuredContent={"ok": False})
    assert call_tool_error_text(result) == "bad input"


async def test_success_result_is_unchanged():
    result = SimpleNamespace(isError=False, content=[text("Useful source excerpt")])
    assert await make_tool(result)() == "Useful source excerpt"


async def test_exception_uses_same_format():
    tool = make_tool(side_effect=RuntimeError("connection reset"))
    assert await tool() == "Error: MCP tool web_search failed: connection reset"
