from abc import ABC, abstractmethod
from typing import Callable, Type
from uin_engine.domain.events import DomainEvent


class IEventBus(ABC):
    """
    An interface (Port) for an event bus.
    It facilitates event-driven, decoupled communication between different
    parts of the application.
    """

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """
        Publishes a domain event to all subscribed handlers.
        """
        pass

    @abstractmethod
    def subscribe(self, event_type: Type[DomainEvent], handler: Callable):
        """
        Subscribes a handler function or method to a specific type of domain event.
        The handler is expected to be an awaitable callable that accepts the event as an argument.
        """
        pass
