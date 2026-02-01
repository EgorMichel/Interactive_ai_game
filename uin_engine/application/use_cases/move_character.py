from uin_engine.application.ports.event_bus import IEventBus
from uin_engine.application.commands.character import MoveCharacterCommand
from uin_engine.domain.events import CharacterMoved
from uin_engine.application.services.memory_service import MemoryService
from uin_engine.domain.entities import GameWorld, Character
from typing import List


class MoveCharacterHandler:
    """
    Handles the MoveCharacterCommand use case.
    This class orchestrates the domain models and infrastructure services
    to fulfill the request.
    """
    def __init__(self, event_bus: IEventBus, memory_service: MemoryService):
        self._bus = event_bus
        self._memory_service = memory_service

    async def execute(self, command: MoveCharacterCommand, world: GameWorld) -> GameWorld:
        """
        Executes the character movement logic on the given world object.
        1. Validates the move.
        2. Updates character's location.
        3. Updates narrative memory for the mover and any observers.
        4. Triggers memory compression check for all affected characters.
        5. Publishes a domain event.
        """
        character = world.characters.get(command.character_id)
        if not character:
            raise ValueError(f"Character with id '{command.character_id}' not found in world.")

        from_location_id = character.location_id
        if from_location_id == command.target_location_id:
            return world

        target_location = world.locations.get(command.target_location_id)
        if not target_location:
            raise ValueError(f"Target location with id '{command.target_location_id}' not found.")

        current_location = world.locations.get(from_location_id)
        if not current_location or command.target_location_id not in current_location.connections:
            raise ValueError(f"Location '{target_location.name}' is not accessible from the character's current location.")

        time_str = world.game_time.strftime('%H:%M')
        
        characters_whose_memory_changed: List[Character] = []

        # 1. Update observers in the source location (before moving)
        for observer in world.characters.values():
            if observer.id != character.id and observer.location_id == from_location_id:
                observer.narrative_memory.append(
                    f"[{time_str}] I saw {character.name} leave the {current_location.name}."
                )
                characters_whose_memory_changed.append(observer)

        # 2. Update character's location
        character.location_id = command.target_location_id
        
        # 3. Log the action for the character who moved
        character.narrative_memory.append(
            f"[{time_str}] I moved from the {current_location.name} to the {target_location.name}."
        )
        characters_whose_memory_changed.append(character)

        # 4. Update observers in the destination location
        for observer in world.characters.values():
            if observer.id != character.id and observer.location_id == command.target_location_id:
                observer.narrative_memory.append(
                    f"[{time_str}] I saw {character.name} arrive at the {target_location.name}."
                )
                characters_whose_memory_changed.append(observer)

        # --- Notify and Compress ---
        event = CharacterMoved(
            character_id=character.id,
            from_location_id=from_location_id,
            to_location_id=command.target_location_id
        )
        await self._bus.publish(event)
        
        # --- Trigger Memory Compression ---
        for char in characters_whose_memory_changed:
            self._memory_service.compress_memory_if_needed(world, char)

        return world

