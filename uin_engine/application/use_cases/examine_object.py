from uin_engine.application.ports.world_repository import IWorldRepository
from uin_engine.application.ports.event_bus import IEventBus
from uin_engine.application.commands.investigation import ExamineObjectCommand
from uin_engine.domain.events import FactDiscovered
from uin_engine.domain.entities import FactId, Clue
from uin_engine.domain.value_objects import KnowledgeEntry
from uin_engine.application.services.memory_service import MemoryService
from typing import List


from uin_engine.domain.entities import FactId, Clue, GameWorld


class ExamineObjectHandler:
    """
    Handles the ExamineObjectCommand use case.
    Allows the player to examine an object in their current location
    and potentially discover new clues/facts.
    """
    def __init__(self, world_repository: IWorldRepository, event_bus: IEventBus, memory_service: MemoryService):
        self._repo = world_repository
        self._bus = event_bus
        self._memory_service = memory_service

    async def execute(self, command: ExamineObjectCommand) -> tuple[List[Clue], GameWorld]:
        """
        Executes the object examination logic.
        1. Fetches world state and validates.
        2. Attempts to discover clues.
        3. Updates player's knowledge (semantic) and memory (episodic).
        4. Triggers memory compression check for the player.
        5. Persists the world state and publishes events.
        """
        world = await self._repo.get_by_id(command.world_id)
        if not world:
            raise ValueError(f"World with id '{command.world_id}' not found.")

        player = world.characters.get(command.player_id)
        if not player:
            raise ValueError(f"Player with id '{command.player_id}' not found.")
        
        if player.location_id != command.location_id:
            raise ValueError(f"Player is not in the expected location '{command.location_id}'.")

        current_location = world.locations.get(command.location_id)
        if not current_location:
            raise ValueError(f"Location with id '{command.location_id}' not found.")

        target_object = next(
            (obj for obj in current_location.objects if obj.id == command.object_id), None
        )
        if not target_object:
            raise ValueError(f"Object with id '{command.object_id}' not found in {current_location.name}.")

        time_str = world.game_time.strftime('%H:%M')
        discovered_clues: List[Clue] = []
        new_facts_for_player: List[FactId] = []

        for clue in target_object.clues:
            if not clue.is_found:
                clue.is_found = True
                discovered_clues.append(clue)
                new_facts_for_player.append(clue.fact_id)
                player.narrative_memory.append(
                    f"[{time_str}] I examined the {target_object.name} and discovered a clue: {clue.description}"
                )
                print(f"You discovered a clue: {clue.description}")

        if not discovered_clues:
            player.narrative_memory.append(
                f"[{time_str}] I examined the {target_object.name} but found nothing new."
            )

        if new_facts_for_player:
            for fact_id in new_facts_for_player:
                player.knowledge[fact_id] = KnowledgeEntry(fact_id=fact_id, certainty=1.0)
            
            await self._repo.save(world)

            for fact_id in new_facts_for_player:
                event = FactDiscovered(
                    character_id=player.id,
                    fact_id=fact_id,
                    location_id=current_location.id,
                    source=f"examining {target_object.name}"
                )
                await self._bus.publish(event)
        else:
            await self._repo.save(world)
        
        # --- Trigger Memory Compression ---
        self._memory_service.compress_memory_if_needed(world, player)

        return discovered_clues, world

