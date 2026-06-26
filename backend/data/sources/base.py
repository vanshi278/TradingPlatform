"""The one interface every market-data feed implements.

A source is just an async generator of normalized `Tick`s tagged with its
`name`. Broker WebSockets, synthetic generators, and historical replay all look
identical to the rest of the system.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from data.models import Tick


class FeedSource(ABC):
    name: str = "base"

    @abstractmethod
    def stream(self) -> AsyncIterator[Tick]:
        """Async generator yielding normalized Ticks (tagged with self.name)."""
        raise NotImplementedError
