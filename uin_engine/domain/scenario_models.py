from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from uin_engine.domain.entities import CharacterId, LocationId, FactId


class ConfigFact(BaseModel):
    """Configuration model for a Fact."""
    id: FactId
    content: str
    is_secret: bool = False


class ConfigClue(BaseModel):
    """Configuration model for a Clue found on an object."""
    fact_id: FactId # The fact discovered when this clue is found
    description: str # Description of the clue itself
    difficulty: float = Field(default=0.0, ge=0.0, le=1.0) # How hard it is to find (0.0 easy, 1.0 hard)


class ConfigObject(BaseModel):
    """Configuration model for an interactive object within a location."""
    id: str # Unique ID for the object within the location context
    name: str # Display name of the object
    description: str # Full description of the object
    clues: List[ConfigClue] = Field(default_factory=list) # Clues associated with this object


class ConfigLocation(BaseModel):
    """Configuration model for a Location."""
    id: LocationId
    name: str
    description: str
    connections: List[LocationId] = Field(default_factory=list)
    properties: Dict[str, Any] = Field(default_factory=dict)
    objects: List[ConfigObject] = Field(default_factory=list)


class ConfigScheduleEntry(BaseModel):
    """Represents a scheduled action for an NPC."""
    time: str # e.g., "08:00", "21:30"
    action_type: str # e.g., "move", "idle", "interact"
    target: Optional[str] = None # e.g., "library" for move, "mark" for interact
    message: Optional[str] = None # For "talk" actions


class ConfigCharacter(BaseModel):
    """Configuration model for a Character."""
    id: CharacterId
    name: str
    description: str
    initial_location: LocationId
    goals: List[str] = Field(default_factory=list)
    initial_knowledge: Dict[FactId, float] = Field(default_factory=dict) # Fact ID to initial certainty
    schedule: List[ConfigScheduleEntry] = Field(default_factory=list)
    # TODO: Add personality, emotional state, relationships


class ConfigSolution(BaseModel):
    """Configuration model for the scenario's solution."""
    killer_id: CharacterId
    required_fact_ids: List[FactId] = Field(default_factory=list)


class ConfigScenario(BaseModel):
    """
    The top-level configuration model for an entire game scenario.
    This will be loaded from a YAML file.
    """
    id: str
    name: str
    description: str
    start_location: LocationId
    player_id: CharacterId = "player" # Assuming player character always has this ID

    locations: List[ConfigLocation] = Field(default_factory=list)
    characters: List[ConfigCharacter] = Field(default_factory=list)
    facts: List[ConfigFact] = Field(default_factory=list)
    solution: Optional[ConfigSolution] = None
