"""Offline checks for the deed.page MCP example (no network, no model)."""

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

try:
    from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool
except ModuleNotFoundError as exc:
    if exc.name != "mcp":
        raise
    MCP_AVAILABLE = False
else:
    MCP_AVAILABLE = True

    import example_deed_page
    from minion_agent.tools.mcp import MCPClient


def text_result(payload, is_error=False):
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return CallToolResult(
        isError=is_error, content=[TextContent(type="text", text=text)]
    )


@unittest.skipUnless(
    MCP_AVAILABLE, "deed.page example tests require the optional MCP dependency"
)
class DeedPageExampleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.token_file = Path(self.tmp.name) / "deed-page" / "token"
        patcher = patch.object(example_deed_page, "TOKEN_FILE", self.token_file)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        env = patch.dict("os.environ", {"DEEDPAGE_TOKEN": ""})
        env.start()
        self.addCleanup(env.stop)

    async def run_example(self, args, responses):
        session = AsyncMock()
        session.list_tools.return_value = ListToolsResult(
            tools=[
                Tool(name=name, inputSchema={"type": "object"})
                for name in ("publish_site", "delete_site")
            ]
        )
        session.call_tool.side_effect = responses
        configs = []

        async def connect(client):
            configs.append(client.config)
            client._session = session

        disconnect = AsyncMock()
        with (
            patch.object(MCPClient, "connect", connect),
            patch.object(MCPClient, "disconnect", disconnect),
            patch("builtins.print") as printed,
        ):
            try:
                await example_deed_page.main(args)
            finally:
                disconnect.assert_awaited_once()
        return session, configs[0], printed

    async def test_first_publish_saves_token_without_printing_it(self):
        args = argparse.Namespace(command="publish", file=None, slug=None, ttl=3600)
        response = {
            "ok": True,
            "url": "https://calm-mesa-1a2b.deed.page/",
            "token": "secret-owner-token",
        }
        session, config, printed = await self.run_example(args, [text_result(response)])
        name, arguments = session.call_tool.await_args.args[:2]
        self.assertEqual(name, "publish_site")
        self.assertEqual(arguments["ttl_seconds"], 3600)
        self.assertIn("index.html", arguments["files"])
        self.assertNotIn("Authorization", config.headers)
        self.assertEqual(self.token_file.read_text().strip(), "secret-owner-token")
        self.assertEqual(self.token_file.stat().st_mode & 0o777, 0o600)
        output = " ".join(str(call.args[0]) for call in printed.call_args_list)
        self.assertIn("https://calm-mesa-1a2b.deed.page/", output)
        self.assertNotIn("secret-owner-token", output)

    async def test_delete_sends_saved_token_as_bearer_header(self):
        self.token_file.parent.mkdir(parents=True)
        self.token_file.write_text("saved-token\n")
        args = argparse.Namespace(command="delete", slug="calm-mesa-1a2b")
        session, config, _ = await self.run_example(
            args, [text_result({"ok": True, "deleted": "calm-mesa-1a2b"})]
        )
        self.assertEqual(config.headers["Authorization"], "Bearer saved-token")
        self.assertEqual(
            session.call_tool.await_args.args[:2],
            ("delete_site", {"slug": "calm-mesa-1a2b"}),
        )

    async def test_tool_error_raises_and_disconnects(self):
        self.token_file.parent.mkdir(parents=True)
        self.token_file.write_text("saved-token\n")
        args = argparse.Namespace(command="delete", slug="gone-site")
        error = text_result(
            '{"code":"not_found","message":"No site at gone-site."}', is_error=True
        )
        with self.assertRaisesRegex(RuntimeError, "not_found"):
            await self.run_example(args, [error])

    async def test_delete_without_token_exits_before_connecting(self):
        args = argparse.Namespace(command="delete", slug="calm-mesa-1a2b")
        with patch.object(MCPClient, "connect", AsyncMock()) as connect:
            with self.assertRaisesRegex(SystemExit, "No owner token"):
                await example_deed_page.main(args)
        connect.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
