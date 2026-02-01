from pydantic import BaseModel

CharacterId = str
LocationId = str


class ExamineObjectCommand(BaseModel):
    """
    A Command DTO representing the intent to examine an object in the current location.
    """
    world_id: str
    player_id: CharacterId
    object_id: str
    location_id: LocationId # Current location where the object is expected


class AccuseCharacterCommand(BaseModel):
    """
    A Command DTO representing the player's intent to accuse another character.
    """
    world_id: str
    player_id: CharacterId
    accused_character_id: CharacterId
