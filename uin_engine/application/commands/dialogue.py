from pydantic import BaseModel
from typing import Optional
from uin_engine.domain.entities import DialogueSessionId

CharacterId = str

class TalkToCharacterCommand(BaseModel):
    """
    A Command DTO representing the intent to initiate or continue a
    conversation with another character.
    """
    world_id: str
    speaker_id: CharacterId     # The character initiating the talk
    listener_id: CharacterId    # The character being spoken to
    message: Optional[str] = None # The message or topic, optional for starting a dialogue
    session_id: Optional[DialogueSessionId] = None # To continue an existing session

class EndDialogueCommand(BaseModel):
    """
    A Command DTO representing the intent to end a dialogue session.
    """
    world_id: str
    session_id: DialogueSessionId
