"""Regression checks for structured MCP failures in the Parallel example."""

import argparse
import unittest
from unittest.mock import AsyncMock, patch

try:
    from mcp.types import (
        CallToolResult,
        ImageContent,
        ListToolsResult,
        TextContent,
        Tool,
    )
except ModuleNotFoundError as exc:
    if exc.name != "mcp":
        raise
    MCP_AVAILABLE = False
else:
    MCP_AVAILABLE = True

    from example_parallel_search import main
    from minion_agent.config import AgentFramework, MCPStreamableHttp
    from minion_agent.tools.mcp import MCPClient


@unittest.skipUnless(
    MCP_AVAILABLE, "Parallel MCP tests require the optional MCP dependency"
)
class MCPErrorTests(unittest.IsolatedAsyncioTestCase):
    async def assert_error_content(self, content, expected):
        client = MCPClient(
            config=MCPStreamableHttp(url="https://search.parallel.ai/mcp"),
            framework=AgentFramework.EXTERNAL_MINION_AGENT,
        )
        client._session = AsyncMock()
        client._session.call_tool.return_value = CallToolResult(
            isError=True, content=content
        )
        tool = client._create_tool_function(
            Tool(name="web_search", inputSchema={"type": "object"})
        )
        self.assertEqual(await tool(), f"Error calling MCP tool web_search: {expected}")

    async def test_single_error_text_is_readable(self):
        await self.assert_error_content(
            [TextContent(type="text", text="Request limit reached")],
            "Request limit reached",
        )

    async def test_multiple_error_text_blocks_are_readable(self):
        await self.assert_error_content(
            [
                TextContent(type="text", text="Request limit reached"),
                TextContent(type="text", text="Try again later"),
            ],
            "Request limit reached\nTry again later",
        )

    async def test_non_text_error_uses_string_fallback(self):
        image = ImageContent(type="image", data="AA==", mimeType="image/png")
        await self.assert_error_content([image], str(image))

    async def test_success_text_is_preserved(self):
        client = MCPClient(
            config=MCPStreamableHttp(url="https://search.parallel.ai/mcp"),
            framework=AgentFramework.EXTERNAL_MINION_AGENT,
        )
        client._session = AsyncMock()
        client._session.call_tool.return_value = CallToolResult(
            content=[TextContent(type="text", text="Useful source excerpt")]
        )
        tool = client._create_tool_function(
            Tool(name="web_search", inputSchema={"type": "object"})
        )
        self.assertEqual(await tool(), "Useful source excerpt")

    async def test_structured_search_error_stops_fetch_and_cleans_up(self):
        session = AsyncMock()
        session.list_tools.return_value = ListToolsResult(
            tools=[
                Tool(name=name, inputSchema={"type": "object"})
                for name in ("web_search", "web_fetch")
            ]
        )
        session.call_tool.return_value = CallToolResult(
            isError=True,
            content=[TextContent(type="text", text="Request limit reached")],
        )

        async def connect(client):
            client._session = session

        disconnect = AsyncMock()
        args = argparse.Namespace(
            objective="Find documentation",
            query=["Python official documentation"],
            url=["https://docs.python.org/3/"],
        )
        with patch.object(MCPClient, "connect", connect), patch.object(
            MCPClient, "disconnect", disconnect
        ), patch("builtins.print") as printed:
            with self.assertRaisesRegex(RuntimeError, "Search failed"):
                await main(args)
        session.call_tool.assert_awaited_once()
        self.assertEqual(session.call_tool.await_args.args[0], "web_search")
        self.assertEqual(
            printed.call_args.args[0],
            "Error calling MCP tool web_search: Request limit reached",
        )
        disconnect.assert_awaited_once()
