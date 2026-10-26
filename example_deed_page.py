"""Publish and delete web pages through Minion Agent's Streamable HTTP MCP client.

deed.page (https://deed.page/docs) hosts static HTML at a public URL with no
account or API key. This example calls its MCP tools directly; it does not
invoke a language model. From the repository root:

    python -m venv .venv
    source .venv/bin/activate
    pip install -e '.[mcp]'
    python example_deed_page.py publish                # sample page, 1-hour expiry
    python example_deed_page.py publish report.html --slug my-report-1234 --ttl 0
    python example_deed_page.py delete my-report-1234

The first publish returns an owner token. It is saved to
~/.config/deed-page/token (mode 600), or read from DEEDPAGE_TOKEN, and sent as
an Authorization header, so later updates and deletes stay with the same owner.
The token is never printed. Published pages are public.

Example by the deed.page team (Avatar 8 LLC); the same server is packaged as an
MIT agent skill at https://github.com/f-o-x11/deed-page-skill
"""

import argparse
import asyncio
import json
import os
from pathlib import Path

from minion_agent.config import AgentFramework, MCPStreamableHttp
from minion_agent.tools.mcp import MCPClient

TOKEN_FILE = Path.home() / ".config" / "deed-page" / "token"
SAMPLE_PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Minion Agent</title></head>
<body><h1>Published with Minion Agent's MCP client</h1></body></html>
"""


def load_token() -> str | None:
    token = os.environ.get("DEEDPAGE_TOKEN", "").strip()
    if not token and TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text().strip()
    return token or None


def save_token(token: str) -> None:
    TOKEN_FILE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    TOKEN_FILE.touch(mode=0o600, exist_ok=True)
    TOKEN_FILE.write_text(token + "\n")
    print(f"Owner token saved to {TOKEN_FILE}")


async def call(tool, **arguments) -> dict:
    text = await tool(**arguments)
    if text.startswith("Error:"):
        raise RuntimeError(text)
    return json.loads(text)


async def main(args: argparse.Namespace) -> None:
    token = load_token()
    if args.command == "delete" and not token:
        raise SystemExit("No owner token; set DEEDPAGE_TOKEN or publish first.")
    headers = {"User-Agent": "minion-agent-x/deed-page-example"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    config = MCPStreamableHttp(
        url="https://deed.page/mcp",
        headers=headers,
        tools=["publish_site", "delete_site"],
        client_session_timeout_seconds=60,
    )
    client = MCPClient(config=config, framework=AgentFramework.EXTERNAL_MINION_AGENT)
    try:
        await client.connect()
        tools = {tool.__name__: tool for tool in await client.list_tools()}
        if args.command == "delete":
            result = await call(tools["delete_site"], slug=args.slug)
            print(f"Deleted {result['deleted']}")
            return
        html = Path(args.file).read_text() if args.file else SAMPLE_PAGE
        arguments = {"files": {"index.html": html}}
        if args.slug:
            arguments["slug"] = args.slug
        if args.ttl:
            arguments["ttl_seconds"] = args.ttl
        result = await call(tools["publish_site"], **arguments)
        if result.get("token"):
            save_token(result["token"])
        print(result["url"])
        if result.get("expires_at"):
            print(f"Expires {result['expires_at']}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Publish or delete a deed.page site over MCP."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    publish = sub.add_parser("publish", help="Publish an HTML file as index.html")
    publish.add_argument("file", nargs="?", help="HTML file (default: a sample page)")
    publish.add_argument("--slug", help="Subdomain to publish to (optional)")
    publish.add_argument(
        "--ttl", type=int, default=3600, help="Seconds until expiry; 0 keeps the page"
    )
    delete = sub.add_parser("delete", help="Delete a page you own")
    delete.add_argument("slug")
    asyncio.run(main(parser.parse_args()))
