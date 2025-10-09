from abc import ABC, abstractmethod
from collections.abc import Sequence
from contextlib import suppress
from typing import Any, Literal

from pydantic import Field, PrivateAttr

from minion_agent.config import AgentFramework, MCPSse, MCPStdio, MCPStreamableHttp
from minion_agent.tools.mcp.mcp_connection import _MCPConnection
from minion_agent.tools.mcp.mcp_server import _MCPServerBase

mcp_available = False
with suppress(ImportError):
    from mcp import StdioServerParameters
    from smolagents.mcp_client import MCPClient
    from smolagents.tools import Tool as MinionTool  # Use smolagents tools for now

    mcp_available = True


class MinionMCPConnection(_MCPConnection["MinionTool"], ABC):
    """Base class for Minion MCP connections."""

    _client: "MCPClient | None" = PrivateAttr(default=None)

    @abstractmethod
    async def list_tools(self) -> list["MinionTool"]:
        """List tools from the MCP server."""
        if not self._client:
            msg = "Tool collection is not set up. Please call `list_tools` from a concrete class."
            raise ValueError(msg)

        tools = self._client.get_tools()
        return self._filter_tools(tools)  # type: ignore[return-value]


class MinionMCPStdioConnection(MinionMCPConnection):
    mcp_tool: MCPStdio

    async def list_tools(self) -> list["MinionTool"]:
        """List tools from the MCP server."""
        server_parameters = StdioServerParameters(
            command=self.mcp_tool.command,
            args=list(self.mcp_tool.args),
            env=self.mcp_tool.env,
        )
        adapter_kwargs = {}
        if self.mcp_tool.client_session_timeout_seconds:
            adapter_kwargs["connect_timeout"] = (
                self.mcp_tool.client_session_timeout_seconds
            )
        self._client = MCPClient(server_parameters, adapter_kwargs=adapter_kwargs)
        return await super().list_tools()


class MinionMCPSseConnection(MinionMCPConnection):
    mcp_tool: MCPSse

    async def list_tools(self) -> list["MinionTool"]:
        """List tools from the MCP server."""
        server_parameters = {"url": self.mcp_tool.url, "transport": "sse"}
        adapter_kwargs = {}
        if self.mcp_tool.client_session_timeout_seconds:
            adapter_kwargs["connect_timeout"] = (
                self.mcp_tool.client_session_timeout_seconds
            )
        self._client = MCPClient(server_parameters, adapter_kwargs=adapter_kwargs)

        return await super().list_tools()


class MinionMCPStreamableHttpConnection(MinionMCPConnection):
    mcp_tool: MCPStreamableHttp

    async def list_tools(self) -> list["MinionTool"]:
        """List tools from the MCP server."""
        server_parameters = {"url": self.mcp_tool.url, "transport": "streamable-http"}
        adapter_kwargs = {}
        if self.mcp_tool.client_session_timeout_seconds:
            adapter_kwargs["connect_timeout"] = (
                self.mcp_tool.client_session_timeout_seconds
            )
        self._client = MCPClient(server_parameters, adapter_kwargs=adapter_kwargs)

        return await super().list_tools()


class MinionMCPServerBase(_MCPServerBase["MinionTool"], ABC):
    framework: Literal[AgentFramework.MINION] = AgentFramework.MINION
    tools: Sequence["MinionTool"] = Field(default_factory=list)

    def _check_dependencies(self) -> None:
        """Check if the required dependencies for the MCP server are available."""
        self.libraries = "minion-agent-x[mcp,smolagents]"  # Use smolagents MCP for now
        self.mcp_available = mcp_available
        super()._check_dependencies()


class MinionMCPServerStdio(MinionMCPServerBase):
    mcp_tool: MCPStdio

    async def _setup_tools(
        self, mcp_connection: _MCPConnection["MinionTool"] | None = None
    ) -> None:
        mcp_connection = mcp_connection or MinionMCPStdioConnection(
            mcp_tool=self.mcp_tool
        )
        await super()._setup_tools(mcp_connection)


class MinionMCPServerSse(MinionMCPServerBase):
    mcp_tool: MCPSse

    async def _setup_tools(
        self, mcp_connection: _MCPConnection["MinionTool"] | None = None
    ) -> None:
        mcp_connection = mcp_connection or MinionMCPSseConnection(
            mcp_tool=self.mcp_tool
        )
        await super()._setup_tools(mcp_connection)


class MinionMCPServerStreamableHttp(MinionMCPServerBase):
    mcp_tool: MCPStreamableHttp

    async def _setup_tools(
        self, mcp_connection: _MCPConnection["MinionTool"] | None = None
    ) -> None:
        mcp_connection = mcp_connection or MinionMCPStreamableHttpConnection(
            mcp_tool=self.mcp_tool
        )
        await super()._setup_tools(mcp_connection)


MinionMCPServer = (
    MinionMCPServerStdio
    | MinionMCPServerSse
    | MinionMCPServerStreamableHttp
)