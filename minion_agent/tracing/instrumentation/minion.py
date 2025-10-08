"""Minion framework instrumentation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.trace import Tracer


class _MinionInstrumentor:
    """Minion framework instrumentation."""

    def __init__(self) -> None:
        self._tracer: Tracer | None = None

    def instrument(self, *, tracer: Tracer) -> None:
        """Instrument the Minion framework."""
        self._tracer = tracer
        # For now, we'll use basic instrumentation
        # This can be extended later with specific Minion framework tracing

    def uninstrument(self) -> None:
        """Uninstrument the Minion framework."""
        self._tracer = None