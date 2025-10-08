"""MCP server implementations for Minion framework."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from minion_agent.tools.mcp.mcp_server import MCPServerStdio, MCPServerSse, MCPServerStreamableHttp

if TYPE_CHECKING:
    from minion_agent.config import MCPSse, MCPStdio, MCPStreamableHttp


class MinionMCPServerStdio(MCPServerStdio[Any]):
    """MCP server for Minion framework using stdio."""

    def __init__(self, *, mcp_tool: MCPStdio) -> None:
        super().__init__(mcp_tool=mcp_tool)

    def _wrap_tool(self, tool: Any) -> Any:
        """Wrap tool for Minion framework."""
        # For now, we'll just return the tool as-is
        # This can be extended later with specific Minion tool wrapping
        return tool


class MinionMCPServerSse(MCPServerSse[Any]):
    """MCP server for Minion framework using SSE."""

    def __init__(self, *, mcp_tool: MCPSse) -> None:
        super().__init__(mcp_tool=mcp_tool)

    def _wrap_tool(self, tool: Any) -> Any:
        """Wrap tool for Minion framework."""
        # For now, we'll just return the tool as-is
        # This can be extended later with specific Minion tool wrapping
        return tool


class MinionMCPServerStreamableHttp(MCPServerStreamableHttp[Any]):
    """MCP server for Minion framework using StreamableHttp."""

    def __init__(self, *, mcp_tool: MCPStreamableHttp) -> None:
        super().__init__(mcp_tool=mcp_tool)

    def _wrap_tool(self, tool: Any) -> Any:
        """Wrap tool for Minion framework."""
        # For now, we'll just return the tool as-is
        # This can be extended later with specific Minion tool wrapping
        return tool