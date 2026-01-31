import asyncio
from datetime import time, timedelta, datetime
from typing import Dict, List, Optional

from uin_engine.domain.entities import GameWorld, CharacterId, Character
from uin_engine.application.ports.world_repository import IWorldRepository
from uin_engine.application.commands.character import MoveCharacterCommand
from uin_engine.application.use_cases.move_character import MoveCharacterHandler

# Assuming a game "tick" represents a specific time duration, e.g., 10 minutes
GAME_TIME_INCREMENT_MINUTES = 10


class NPCBehaviorSystem:
    """
    Manages the autonomous behavior of NPCs based on their schedules and game time.
    """
    def __init__(
        self,
        world_repository: IWorldRepository,
        move_character_handler: MoveCharacterHandler,
        # Potentially other handlers for talk, investigate, etc.
    ):
        self._repo = world_repository
        self._move_handler = move_character_handler
        # self._talk_handler = talk_character_handler

    async def update_game_time(self, world: GameWorld) -> GameWorld:
        """
        Advances the game time by a fixed increment.
        """
        # Convert current game_time to a datetime object for easy arithmetic
        dt_current_time = datetime.combine(datetime.min, world.game_time)
        
        # Add the increment
        dt_new_time = dt_current_time + timedelta(minutes=GAME_TIME_INCREMENT_MINUTES)
        
        # Update world's game_time, keeping only the time part
        world.game_time = dt_new_time.time()
        
        return world

    async def execute_npc_behaviors(self, world: GameWorld) -> GameWorld:
        """
        Iterates through all NPCs and executes their scheduled actions
        if the current game time matches their schedule. Returns the updated world.
        """
        current_game_time = world.game_time
        print(f"[{current_game_time.strftime('%H:%M')}] NPC Update Cycle:")

        for character_id, character in world.characters.items():
            if character_id == world.player_id: # Skip player character
                continue
            
            # Find a schedule entry that matches the current game time
            for entry in character.schedule:
                # Compare only time part
                if time.fromisoformat(entry.time) == current_game_time:
                    print(f"  {character.name} is performing scheduled action: {entry.action_type} at {entry.time}")
                    world = await self._perform_scheduled_action(world, character, entry)
                    # Assuming only one action per time slot for simplicity
                    break
        return world
    
    async def _perform_scheduled_action(self, world: GameWorld, character: Character, entry) -> GameWorld:
        """
        Executes a specific scheduled action for an NPC and returns the updated world.
        """
        if entry.action_type == "move" and entry.target:
            try:
                command = MoveCharacterCommand(
                    world_id=world.id,
                    character_id=character.id,
                    target_location_id=entry.target
                )
                world = await self._move_handler.execute(command)
                print(f"    - {character.name} moved to {entry.target}.")
            except ValueError as e:
                print(f"    - {character.name} failed to move to {entry.target}: {e}")
        # TODO: Add logic for "talk", "idle", etc.
        return world
