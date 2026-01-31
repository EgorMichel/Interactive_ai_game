from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pydantic import BaseModel, Field

# Note: Using str for IDs here to avoid circular dependencies with entities
# A more advanced setup might use a central types file.
CharacterId = str
LocationId = str
FactId = str


class DomainEvent(BaseModel, ABC):
    """
    An abstract base class for domain events.
    Represents something significant that has happened in the domain.
    """
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    @abstractmethod
    def name(self) -> str:
        """A unique, machine-readable name for the event."""
        pass


class CharacterMoved(DomainEvent):
    """Event triggered when a character moves from one location to another."""
    character_id: CharacterId
    from_location_id: LocationId
    to_location_id: LocationId

    @property
    def name(self) -> str:
        return "character.moved"


class FactDiscovered(DomainEvent):
    """Event triggered when a character discovers a new fact."""
    character_id: CharacterId
    fact_id: FactId
    location_id: LocationId | None = None
    source: str | None = None  # e.g., "investigation", "dialogue"

    @property
    def name(self) -> str:
        return "fact.discovered"

class DialogueOccurred(DomainEvent):
    """Event triggered after a dialogue between two characters."""
    speaker_id: CharacterId
    listener_id: CharacterId
    dialogue_text: str
    revealed_fact_ids: list[FactId] = Field(default_factory=list)

    @property
    def name(self) -> str:
        return "dialogue.occurred"
