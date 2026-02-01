import pytest
from datetime import time, timedelta, datetime
from unittest.mock import AsyncMock

from uin_engine.domain.entities import GameWorld, Character, Location, CharacterId, LocationId, ScheduleEntry
from uin_engine.application.services.npc_behavior_system import NPCBehaviorSystem, GAME_TIME_INCREMENT_MINUTES
from uin_engine.infrastructure.repositories.in_memory_world_repository import InMemoryWorldRepository
from uin_engine.application.use_cases.move_character import MoveCharacterHandler # Actual handler, not mock


@pytest.fixture
def test_world():
    """Fixture to create a basic GameWorld for testing NPC behaviors."""
    player_id = CharacterId("player")
    sophie_id = CharacterId("sophie")
    mark_id = CharacterId("mark")

    bridge = Location(id=LocationId("bridge"), name="Bridge", description="bridge", connections=["lounge"])
    lounge = Location(id=LocationId("lounge"), name="Lounge", description="lounge", connections=["bridge"])

    player = Character(id=player_id, name="Player", description="player", location_id="bridge")
    sophie = Character(
        id=sophie_id,
        name="Sophie",
        description="sophie",
        location_id="lounge",
        schedule=[
            ScheduleEntry(time="08:10", action_type="move", target="bridge"),
            ScheduleEntry(time="08:20", action_type="idle"),
        ]
    )
    mark = Character(
        id=mark_id,
        name="Mark",
        description="mark",
        location_id="bridge",
        schedule=[
            ScheduleEntry(time="08:10", action_type="idle"),
            ScheduleEntry(time="08:20", action_type="move", target="lounge"),
        ]
    )

    world = GameWorld(
        id="test_world",
        name="Test World",
        player_id=player_id,
        locations={bridge.id: bridge, lounge.id: lounge},
        characters={player.id: player, sophie.id: sophie, mark.id: mark},
        game_time=time(8, 0) # Start at 08:00
    )
    return world


@pytest.mark.asyncio
async def test_update_game_time(test_world):
    """Tests that game time is correctly advanced."""
    repo = InMemoryWorldRepository()
    await repo.save(test_world)
    
    move_handler = AsyncMock(spec=MoveCharacterHandler)
    system = NPCBehaviorSystem(move_character_handler=move_handler)

    initial_time = test_world.game_time
    updated_world = await system.update_game_time(test_world)
    await repo.save(updated_world) # Save after time update

    expected_time = (datetime.combine(datetime.min, initial_time) + timedelta(minutes=GAME_TIME_INCREMENT_MINUTES)).time()
    assert updated_world.game_time == expected_time


@pytest.mark.asyncio
async def test_execute_npc_behaviors_moves_character(test_world):
    """
    Tests that an NPC's scheduled move action is correctly executed.
    """
    repo = InMemoryWorldRepository()
    await repo.save(test_world) # Save initial world state

    move_handler = AsyncMock(spec=MoveCharacterHandler) # Mock the handler
    system = NPCBehaviorSystem(move_character_handler=move_handler)

    # Set game time to trigger Sophie's move (08:10)
    test_world.game_time = time(8, 10)
    await repo.save(test_world) # Update world time in repo

    # Execute behaviors
    await system.execute_npc_behaviors(test_world)

    # Assert move_handler was called for Sophie
    move_handler.execute.assert_called_once()
    call_args, _ = move_handler.execute.call_args
    command = call_args[0]
    assert command.character_id == CharacterId("sophie")
    assert command.target_location_id == LocationId("bridge")

    # Assert that the world repository was saved by the handler (implicitly via move_handler)
    # The NPCBehaviorSystem itself doesn't save *after* actions, the handlers do.
    # We can check the world state directly if the handler wasn't mocked.
    # For now, just ensure the handler was called.


@pytest.mark.asyncio
async def test_execute_npc_behaviors_no_action_if_time_does_not_match(test_world):
    """
    Tests that no scheduled actions are executed if the game time
    does not match any schedule entries.
    """
    repo = InMemoryWorldRepository()
    await repo.save(test_world)

    move_handler = AsyncMock(spec=MoveCharacterHandler)
    system = NPCBehaviorSystem(move_character_handler=move_handler)

    # Set game time to something not in schedule (e.g., 08:05)
    test_world.game_time = time(8, 5)
    await repo.save(test_world)

    await system.execute_npc_behaviors(test_world)

    # Assert no handler was called
    move_handler.execute.assert_not_called()

