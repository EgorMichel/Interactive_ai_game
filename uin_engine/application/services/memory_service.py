import asyncio
from typing import List

from uin_engine.application.ports.llm_service import ILLMService
from uin_engine.application.ports.world_repository import IWorldRepository
from uin_engine.domain.entities import Character, GameWorld


class MemoryService:
    """
    Handles advanced memory operations for characters, like summarization.
    """

    def __init__(self, llm_service: ILLMService, world_repository: IWorldRepository):
        self._llm_service = llm_service
        self._repo = world_repository

    async def _summarize_chunk(self, world_id: str, character_id: str, chunk: List[str]):
        """
        Private method to perform summarization in the background.
        It fetches the latest world and character state to avoid race conditions.
        """
        try:
            print(f"[MemoryService] Background task started for {character_id}...")
            text_to_summarize = "\n".join(chunk)
            summary = await self._llm_service.summarize(text_to_summarize)

            # Fetch the LATEST world state right before mutation
            world = await self._repo.get_by_id(world_id)
            if not world:
                print(f"[MemoryService] ERROR: World {world_id} not found during summarization.")
                return

            character = world.characters.get(character_id)
            if not character:
                print(f"[MemoryService] ERROR: Character {character_id} not found during summarization.")
                return

            # Create a new memory list with the summary replacing the old chunk
            # This logic assumes the chunk is from the start of the list.
            current_memory = character.narrative_memory
            new_memory = [summary] + current_memory[len(chunk):]
            character.narrative_memory = new_memory

            await self._repo.save(world)
            print(f"[MemoryService] Background task finished for {character_id}. Memory compressed.")

        except Exception as e:
            print(f"[MemoryService] ERROR in background summarization task: {e}")

    def compress_memory_if_needed(
        self, 
        world: GameWorld, 
        character: Character, 
        threshold: int = 15, 
        items_to_summarize: int = 10
    ):
        """
        Checks if a character's narrative memory exceeds a threshold and, if so,
        schedules a background task to summarize the oldest part of it.
        """
        if len(character.narrative_memory) > threshold:
            print(f"[MemoryService] Memory for {character.name} reached {len(character.narrative_memory)} entries. Scheduling compression.")
            
            # Get the chunk to summarize from the beginning of the list
            chunk_to_summarize = character.narrative_memory[:items_to_summarize]
            
            # Schedule the summarization to run in the background
            asyncio.create_task(self._summarize_chunk(world.id, character.id, chunk_to_summarize))
