import asyncio
from typing import List

from uin_engine.application.ports.llm_service import ILLMService
from uin_engine.domain.entities import Character


class MemoryService:
    """
    Handles advanced memory operations for characters, like summarization.
    """

    def __init__(self, llm_service: ILLMService):
        self._llm_service = llm_service

    async def summarize_and_add_to_memory(
        self,
        character: Character,
        dialogue_replicas: List[str]
    ):
        """
        Takes a list of dialogue strings, summarizes them, and appends the
        single summary string to the character's long-term narrative memory.
        """
        if not dialogue_replicas:
            return
            
        print(f"[MemoryService] Summarizing conversation for {character.name}...")
        text_to_summarize = "\n".join(dialogue_replicas)
        
        summary = await self._llm_service.summarize(text_to_summarize)
        
        # Append the summary to the character's long-term memory
        character.narrative_memory.append(summary)
        
        print(f"[MemoryService] Conversation summary added to {character.name}'s memory.")
