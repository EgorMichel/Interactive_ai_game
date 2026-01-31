from uin_engine.application.ports.world_repository import IWorldRepository
from uin_engine.application.ports.event_bus import IEventBus
from uin_engine.application.commands.investigation import ExamineObjectCommand
from uin_engine.domain.events import FactDiscovered
from uin_engine.domain.entities import FactId, Clue
from uin_engine.domain.value_objects import KnowledgeEntry
from typing import List


from uin_engine.domain.entities import FactId, Clue, GameWorld


class ExamineObjectHandler:
    """
    Handles the ExamineObjectCommand use case.
    Allows the player to examine an object in their current location
    and potentially discover new clues/facts.
    """
    def __init__(self, world_repository: IWorldRepository, event_bus: IEventBus):
        self._repo = world_repository
        self._bus = event_bus

    async def execute(self, command: ExamineObjectCommand) -> tuple[List[Clue], GameWorld]:
        """
        Executes the object examination logic.

        1. Fetches the world state.
        2. Validates player and object existence/location.
        3. Attempts to discover clues.
        4. Updates player knowledge with newly found facts.
        5. Persists the world state.
        6. Publishes FactDiscovered events.
        7. Returns a list of newly discovered clues and the updated world.
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

        discovered_clues: List[Clue] = []
        new_facts_for_player: List[FactId] = []

        for clue in target_object.clues:
            if not clue.is_found: # Only discover if not already found
                # For now, always discover the clue (difficulty always passed)
                # In the future, this is where skill checks/difficulty would come in
                clue.is_found = True # Mark clue as found
                discovered_clues.append(clue)
                new_facts_for_player.append(clue.fact_id)
                print(f"You discovered a clue: {clue.description}")

        if new_facts_for_player:
            for fact_id in new_facts_for_player:
                player.knowledge[fact_id] = KnowledgeEntry(fact_id=fact_id, certainty=1.0)
            
            await self._repo.save(world) # Save world state after updating player knowledge

            for fact_id in new_facts_for_player:
                event = FactDiscovered(
                    character_id=player.id,
                    fact_id=fact_id,
                    location_id=current_location.id,
                    source=f"examining {target_object.name}"
                )
                await self._bus.publish(event)
        
        return discovered_clues, world

