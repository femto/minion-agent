"""Compatibility helpers for MCP Python SDK 1.x and 2.x.

MCP 2.x changed a few client APIs that minion_agent relies on (ported from minion):
- ``streamablehttp_client`` was removed; ``streamable_http_client`` takes a
  pre-configured ``httpx2.AsyncClient`` and yields ``(read, write)`` only.
- ``ClientSession(read_timeout_seconds=...)`` takes seconds as a float
  instead of a ``timedelta``.
- Type fields are snake_case (``input_schema``, ``structured_content``,
  ``mime_type``) instead of camelCase.
"""

from contextlib import AsyncExitStack
from datetime import timedelta
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Dict, Optional, Tuple, Union


def _mcp_major_version() -> int:
    try:
        return int(version("mcp").split(".")[0])
    except (PackageNotFoundError, ValueError):
        return 1


MCP_V2 = _mcp_major_version() >= 2

DEFAULT_HTTP_TIMEOUT = 30.0
DEFAULT_SSE_READ_TIMEOUT = 300.0


def _seconds(value: Optional[Union[float, timedelta]]) -> Optional[float]:
    if isinstance(value, timedelta):
        return value.total_seconds()
    return value


def session_read_timeout(value: Optional[Union[float, timedelta]]) -> Optional[Union[float, timedelta]]:
    """Convert a read timeout to the type ``ClientSession`` expects."""
    if value is None:
        return None
    if MCP_V2:
        return _seconds(value)
    return value if isinstance(value, timedelta) else timedelta(seconds=value)


def get_field(obj: Any, snake_name: str, camel_name: str, default: Any = None) -> Any:
    """Read an MCP type field under its 2.x (snake_case) or 1.x (camelCase) name."""
    value = getattr(obj, snake_name, None)
    if value is None:
        value = getattr(obj, camel_name, default)
    return value


async def open_streamable_http(
    exit_stack: AsyncExitStack,
    url: str,
    headers: Optional[Dict[str, Any]] = None,
    timeout: Optional[Union[float, timedelta]] = None,
    sse_read_timeout: Optional[Union[float, timedelta]] = None,
    terminate_on_close: Optional[bool] = None,
    auth: Optional[Any] = None,
) -> Tuple[Any, Any]:
    """Open a Streamable HTTP transport on ``exit_stack`` and return ``(read, write)``.

    ``auth`` must be an ``httpx.Auth`` with MCP 1.x, or an ``httpx2.Auth`` with MCP 2.x.
    """
    if not MCP_V2:
        from mcp.client.streamable_http import streamablehttp_client

        client_kwargs: Dict[str, Any] = {"url": url}
        if headers:
            client_kwargs["headers"] = headers
        if timeout is not None:
            client_kwargs["timeout"] = timeout
        if sse_read_timeout is not None:
            client_kwargs["sse_read_timeout"] = sse_read_timeout
        if terminate_on_close is not None:
            client_kwargs["terminate_on_close"] = terminate_on_close
        if auth is not None:
            client_kwargs["auth"] = auth
        read, write, _ = await exit_stack.enter_async_context(streamablehttp_client(**client_kwargs))
        return read, write

    import httpx2
    from mcp.client.streamable_http import streamable_http_client

    http_timeout = _seconds(timeout)
    read_timeout = _seconds(sse_read_timeout)
    client_kwargs = {
        "timeout": httpx2.Timeout(
            DEFAULT_HTTP_TIMEOUT if http_timeout is None else http_timeout,
            read=DEFAULT_SSE_READ_TIMEOUT if read_timeout is None else read_timeout,
        )
    }
    if headers:
        client_kwargs["headers"] = headers
    if auth is not None:
        client_kwargs["auth"] = auth
    http_client = await exit_stack.enter_async_context(httpx2.AsyncClient(**client_kwargs))

    transport_kwargs: Dict[str, Any] = {"http_client": http_client}
    if terminate_on_close is not None:
        transport_kwargs["terminate_on_close"] = terminate_on_close
    read, write = await exit_stack.enter_async_context(streamable_http_client(url, **transport_kwargs))
    return read, write
