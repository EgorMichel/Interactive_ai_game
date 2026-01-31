import asyncio
from collections import defaultdict
from typing import Callable, Type, List, Dict, Awaitable

from uin_engine.domain.events import DomainEvent
from uin_engine.application.ports.event_bus import IEventBus

# Type alias for an awaitable handler
EventHandler = Callable[[DomainEvent], Awaitable[None]]


class LocalEventBus(IEventBus):
    """
    A simple in-process implementation of the event bus.
    It manages subscriptions in memory and calls handlers asynchronously.
    This is suitable for a single-process application.
    """
    _subscriptions: Dict[Type[DomainEvent], List[EventHandler]]

    def __init__(self):
        self._subscriptions = defaultdict(list)

    def subscribe(self, event_type: Type[DomainEvent], handler: EventHandler):
        """Subscribes a handler to a specific event type."""
        self._subscriptions[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        """
        Finds all handlers subscribed to the specific event's type
        and executes them concurrently.
        """
        handlers = self._subscriptions[type(event)]
        if handlers:
            # Use asyncio.gather to run all handlers for this event concurrently
            await asyncio.gather(*(handler(event) for handler in handlers))
