from pydantic import BaseModel

CharacterId = str

class TalkToCharacterCommand(BaseModel):
    """
    A Command DTO representing the intent to initiate or continue a
    conversation with another character.
    """
    world_id: str
    speaker_id: CharacterId     # The character initiating the talk
    listener_id: CharacterId    # The character being spoken to
    message: str                # The message or topic of conversation
