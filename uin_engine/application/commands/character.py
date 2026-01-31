from pydantic import BaseModel

# Using simple strings for now, but aliased types from the domain can be used.
CharacterId = str
LocationId = str


class MoveCharacterCommand(BaseModel):
    """
    A Command Data Transfer Object (DTO).
    It represents a specific, atomic intent to change the system's state.
    In this case, the intent is to move a character to a new location.
    """
    world_id: str
    character_id: CharacterId
    target_location_id: LocationId
