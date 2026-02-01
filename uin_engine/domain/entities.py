from pydantic import BaseModel, Field
from typing import NewType, List, Dict, Any, Optional

from uin_engine.domain.value_objects import KnowledgeEntry, Relationship

# Using NewType for semantic clarity in the domain model.
# These act as aliases but can help type checkers be more strict.
CharacterId = NewType('CharacterId', str)
LocationId = NewType('LocationId', str)
FactId = NewType('FactId', str)
DialogueSessionId = NewType('DialogueSessionId', str)


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

    # Level 3 Memory: Semantic (Structured Facts)
    knowledge: Dict[FactId, KnowledgeEntry] = Field(default_factory=dict)
    
    # Level 2 Memory: Episodic (Narrative Log of summaries and key events)
    narrative_memory: List[str] = Field(default_factory=list)

    relationships: Dict[CharacterId, Relationship] = Field(default_factory=dict)
    emotional_state: Dict[str, float] = Field(default_factory=dict)  # e.g., {"fear": 0.8, "trust": 0.2}
    goals: List[str] = Field(default_factory=list)
    schedule: List[ScheduleEntry] = Field(default_factory=list) # Schedule for the NPC


from datetime import time

class DialogueReplica(BaseModel):
    """A single replica within a dialogue session."""
    speaker_id: CharacterId
    message: str
    game_time: time


class DialogueSession(BaseModel):
    """Represents an active dialogue session between characters."""
    id: DialogueSessionId
    participants: List[CharacterId]
    history: List[DialogueReplica] = Field(default_factory=list)
    is_active: bool = True


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
    game_time: time = Field(default_factory=lambda: time(8, 0))
    active_dialogues: Dict[DialogueSessionId, DialogueSession] = Field(default_factory=dict)
    solution: Optional['Solution'] = None

class Solution(BaseModel):
    """Represents the solution to the mystery."""
    killer_id: CharacterId
    required_fact_ids: List[FactId] = Field(default_factory=list)

# This is a forward reference fix. Pydantic needs to know about the Solution model
# before it's used in GameWorld. By updating the forward references after both are
# defined, we resolve the dependency cycle.
GameWorld.model_rebuild()

