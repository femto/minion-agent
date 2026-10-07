"""Call Parallel search/fetch through Minion Agent's Streamable HTTP MCP client.

This example executes tools directly; it does not invoke a language model.
See README.md for installation and command-line usage.
"""

import argparse
import asyncio
from uuid import uuid4

from minion_agent.config import AgentFramework, MCPStreamableHttp
from minion_agent.tools.mcp import MCPClient


async def main(args: argparse.Namespace) -> None:
    config = MCPStreamableHttp(
        url="https://search.parallel.ai/mcp",
        headers={"User-Agent": "minion-agent-x/parallel-search-example"},
        tools=["web_search", "web_fetch"],
        client_session_timeout_seconds=60,
    )
    client = MCPClient(config=config, framework=AgentFramework.EXTERNAL_MINION_AGENT)
    session_id = str(uuid4())
    try:
        await client.connect()
        tools = {tool.__name__: tool for tool in await client.list_tools()}
        search = await tools["web_search"](
            objective=args.objective,
            search_queries=args.query,
            session_id=session_id,
        )
        print(search)
        if search.startswith("Error"):
            raise RuntimeError("Search failed; see the tool response above.")
        if args.url:
            fetched = await tools["web_fetch"](
                urls=args.url,
                objective=args.objective,
                search_queries=args.query,
                session_id=session_id,
            )
            print(fetched)
            if fetched.startswith("Error"):
                raise RuntimeError("Fetch failed; see the tool response above.")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("objective", help="A focused description of what to find")
    parser.add_argument(
        "--query",
        action="append",
        required=True,
        help="Search query; repeat for related queries",
    )
    parser.add_argument(
        "--url", action="append", help="Also fetch this URL; repeat for related pages"
    )
    asyncio.run(main(parser.parse_args()))
