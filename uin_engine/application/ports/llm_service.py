from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import List


# Data Transfer Objects (DTOs) for the LLM service interface.
# These prevent the domain from being tightly coupled to the LLM's specific API.

class DialogueGenerationContext(BaseModel):
    """
    Input context for generating a single dialogue line for a character.
    """
    speaker_name: str
    speaker_description: str
    speaker_goals: List[str]
    speaker_knowledge: str  # A summary of what the speaker knows.
    listener_name: str
    listener_description: str # Description of the character listening
    listener_goals: List[str] # Goals of the character listening
    listener_knowledge: str # A summary of what the listener knows.
    recent_dialogue_history: str
    current_topic: str


class DialogueGenerationResponse(BaseModel):
    """
    Output from the LLM after generating a dialogue line.
    """
    text: str
    # The LLM can suggest new facts that were revealed.
    newly_revealed_facts: List[str] = []
    # The LLM can indicate a change in the character's emotional state.
    emotional_impact: dict[str, float] = {}


class ILLMService(ABC):
    """
    An interface (Port) for interacting with a Large Language Model
    to generate dialogue and other narrative content.
    """

    @abstractmethod
    async def generate_dialogue(self, context: DialogueGenerationContext) -> DialogueGenerationResponse:
        """
        Generates a single dialogue response based on the given context.
        """
        pass

    @abstractmethod
    async def batch_generate_dialogues(self, contexts: List[DialogueGenerationContext]) -> List[DialogueGenerationResponse]:
        """
        Generates multiple dialogue responses in a single batch call for efficiency.
        """
        pass
