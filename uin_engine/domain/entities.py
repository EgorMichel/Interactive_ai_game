from pydantic import BaseModel, Field
from typing import NewType, List, Dict, Any, Optional

from uin_engine.domain.value_objects import KnowledgeEntry, Relationship

# Using NewType for semantic clarity in the domain model.
# These act as aliases but can help type checkers be more strict.
CharacterId = NewType('CharacterId', str)
LocationId = NewType('LocationId', str)
FactId = NewType('FactId', str)


class Fact(BaseModel):
    """Represents a statement about the world that can be known by characters."""
    id: FactId
    content: str
    is_secret: bool = False


class Clue(BaseModel):
    """Represents a clue that can be found in the game, linked to a Fact."""
    fact_id: FactId
    description: str # Description of the clue itself, for player
    difficulty: float = Field(default=0.0, ge=0.0, le=1.0) # How hard it is to find (0.0 easy, 1.0 hard)
    is_found: bool = False


class GameObject(BaseModel):
    """Represents an interactive object within a location."""
    id: str # Unique ID for the object within the location context
    name: str # Display name of the object
    description: str # Full description of the object
    clues: List[Clue] = Field(default_factory=list) # Clues associated with this object


class Location(BaseModel):
    """A place in the game world where characters can be and events can occur."""
    id: LocationId
    name: str
    description: str
    connections: List[LocationId] = Field(default_factory=list)
    properties: Dict[str, Any] = Field(default_factory=dict)  # e.g., {"lighting": "dim", "sound_proof": false}
    objects: List[GameObject] = Field(default_factory=list) # Interactive objects in this location


class ScheduleEntry(BaseModel):
    """Represents a scheduled action for an NPC."""
    time: str # e.g., "08:00", "21:30"
    action_type: str # e.g., "move", "idle", "interact"
    target: Optional[str] = None # e.g., "library" for move, "mark" for interact
    message: Optional[str] = None # For "talk" actions


class Character(BaseModel):
    """
    Represents an agent in the game world (player or NPC).
    Characters have knowledge, relationships, and an emotional state.
    """
    id: CharacterId
    name: str
    description: str
    location_id: LocationId  # The current location of the character

    knowledge: Dict[FactId, KnowledgeEntry] = Field(default_factory=dict)
    relationships: Dict[CharacterId, Relationship] = Field(default_factory=dict)
    emotional_state: Dict[str, float] = Field(default_factory=dict)  # e.g., {"fear": 0.8, "trust": 0.2}
    goals: List[str] = Field(default_factory=list)
    schedule: List[ScheduleEntry] = Field(default_factory=list) # Schedule for the NPC


from datetime import time
class DialogueEntry(BaseModel):
    """Represents a single entry in a dialogue history."""
    speaker_id: CharacterId
    listener_id: CharacterId
    message: str
    game_time: time


class GameWorld(BaseModel):
    """
    The aggregate root for the game state.
    It encapsulates the entire state of the game world, ensuring its consistency.
    """
    id: str  # Typically the scenario ID
    name: str
    player_id: CharacterId
    locations: Dict[LocationId, Location] = Field(default_factory=dict)
    characters: Dict[CharacterId, Character] = Field(default_factory=dict)
    facts: Dict[FactId, Fact] = Field(default_factory=dict)
    game_time: time = Field(default_factory=lambda: time(8, 0))  # Start at 08:00 by default
    dialogue_history: List[DialogueEntry] = Field(default_factory=list) # Add dialogue history

