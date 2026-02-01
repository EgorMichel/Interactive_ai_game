import asyncio
from collections import defaultdict
from typing import Callable, Type, List, Dict, Awaitable, Optional

from uin_engine.domain.events import DomainEvent
from uin_engine.domain.entities import GameWorld
from uin_engine.application.ports.event_bus import IEventBus

# Type alias for an awaitable handler that now accepts the world context
EventHandler = Callable[[DomainEvent, Optional[GameWorld]], Awaitable[None]]


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

    async def publish(self, event: DomainEvent, world: Optional[GameWorld] = None) -> None:
        """
        Finds all handlers subscribed to the event's type (or its parent types)
        and executes them concurrently, passing both the event and the world.
        """
        event_type = type(event)
        
        # Collect handlers for the specific type and all its parent event types
        # This allows subscribing to a generic DomainEvent to catch all events.
        handlers_to_run = []
        for subscribed_type, handlers in self._subscriptions.items():
            if isinstance(event, subscribed_type):
                handlers_to_run.extend(handlers)
        
        if handlers_to_run:
            # Use asyncio.gather to run all handlers concurrently
            await asyncio.gather(*(handler(event, world) for handler in handlers_to_run))
