"""Regression checks for structured MCP failures in the Parallel example."""

import argparse
import unittest
from unittest.mock import AsyncMock, patch

try:
    from mcp.types import (
        CallToolResult,
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
    from minion_agent.tools.mcp import MCPClient


@unittest.skipUnless(
    MCP_AVAILABLE, "Parallel MCP tests require the optional MCP dependency"
)
class MCPErrorTests(unittest.IsolatedAsyncioTestCase):
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
        with (
            patch.object(MCPClient, "connect", connect),
            patch.object(MCPClient, "disconnect", disconnect),
            patch("builtins.print") as printed,
        ):
            with self.assertRaisesRegex(RuntimeError, "Search failed"):
                await main(args)
        session.call_tool.assert_awaited_once()
        self.assertEqual(session.call_tool.await_args.args[0], "web_search")
        self.assertEqual(
            printed.call_args.args[0],
            "Error: MCP tool web_search failed: Request limit reached",
        )
        disconnect.assert_awaited_once()

    async def run_example(self, responses):
        session = AsyncMock()
        session.list_tools.return_value = ListToolsResult(
            tools=[
                Tool(name=name, inputSchema={"type": "object"})
                for name in ("web_search", "web_fetch")
            ]
        )
        session.call_tool.side_effect = responses

        async def connect(client):
            client._session = session

        disconnect = AsyncMock()
        args = argparse.Namespace(
            objective="Find documentation",
            query=["Python official documentation"],
            url=["https://docs.python.org/3/"],
        )
        with (
            patch.object(MCPClient, "connect", connect),
            patch.object(MCPClient, "disconnect", disconnect),
            patch("builtins.print") as printed,
        ):
            try:
                await main(args)
            finally:
                disconnect.assert_awaited_once()
        return session, printed

    async def test_success_beginning_error_still_fetches_and_cleans_up(self):
        responses = [
            CallToolResult(content=[TextContent(type="text", text=text)])
            for text in ("Error handling documentation", "Error recovery guide")
        ]
        session, printed = await self.run_example(responses)
        self.assertEqual(
            [call.args[0] for call in session.call_tool.await_args_list],
            ["web_search", "web_fetch"],
        )
        self.assertEqual(
            [call.args[0] for call in printed.call_args_list],
            ["Error handling documentation", "Error recovery guide"],
        )
        self.assertEqual(
            session.call_tool.await_args_list[0].args[1]["session_id"],
            session.call_tool.await_args_list[1].args[1]["session_id"],
        )

    async def test_structured_fetch_error_fails_and_cleans_up(self):
        responses = [
            CallToolResult(content=[TextContent(type="text", text="Source excerpt")]),
            CallToolResult(
                isError=True,
                content=[TextContent(type="text", text="Request limit reached")],
            ),
        ]
        with self.assertRaisesRegex(RuntimeError, "Fetch failed"):
            await self.run_example(responses)
