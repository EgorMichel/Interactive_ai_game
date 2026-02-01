import pytest
from unittest.mock import Mock, AsyncMock

from uin_engine.domain.entities import GameWorld, Character, Location, CharacterId, LocationId
from uin_engine.domain.events import CharacterMoved
from uin_engine.infrastructure.repositories.in_memory_world_repository import InMemoryWorldRepository
from uin_engine.infrastructure.event_bus.local_event_bus import LocalEventBus
from uin_engine.application.use_cases.move_character import MoveCharacterHandler
from uin_engine.application.commands.character import MoveCharacterCommand
from uin_engine.application.services.memory_service import MemoryService # Import MemoryService

@pytest.mark.asyncio
async def test_move_character_successfully():
    """
    Tests the happy path: a valid character moves to a valid, connected location.
    Verifies that the world state is updated and an event is published.
    """
    # 1. ARRANGE
    world_repo = InMemoryWorldRepository()
    event_bus = LocalEventBus()
    mock_memory_service = AsyncMock(spec=MemoryService) # Mock MemoryService
    handler = MoveCharacterHandler(event_bus=event_bus, memory_service=mock_memory_service)

    # Create a mock handler to spy on the event bus
    event_handler_mock = AsyncMock()
    event_bus.subscribe(CharacterMoved, event_handler_mock)

    # Create and save the initial world state
    char_id = CharacterId("player")
    start_loc_id = LocationId("bridge")
    end_loc_id = LocationId("engine_room")

    test_world = GameWorld(
        id="test_scenario",
        name="Test Scenario",
        player_id=char_id,
        locations={
            start_loc_id: Location(id=start_loc_id, name="Bridge", description="...", connections=[end_loc_id]),
            end_loc_id: Location(id=end_loc_id, name="Engine Room", description="..."),
        },
        characters={
            char_id: Character(id=char_id, name="Player", description="player description", location_id=start_loc_id) # Added description
        }
    )
    await world_repo.save(test_world)

    command = MoveCharacterCommand(
        world_id="test_scenario",
        character_id=char_id,
        target_location_id=end_loc_id
    )

    # 2. ACT
    updated_world = await handler.execute(command, test_world) # Pass world to execute

    # 3. ASSERT
    # Assert world state has changed correctly (using updated_world from handler)
    moved_character = updated_world.characters.get(char_id)
    assert moved_character.location_id == end_loc_id

    # Assert that the correct event was published and caught by our spy
    event_handler_mock.assert_called_once()
    published_event = event_handler_mock.call_args[0][0]
    assert isinstance(published_event, CharacterMoved)
    assert published_event.character_id == char_id
    assert published_event.from_location_id == start_loc_id
    assert published_event.to_location_id == end_loc_id

    # Assert memory service was called
    mock_memory_service.compress_memory_if_needed.assert_called_once_with(updated_world, moved_character)


@pytest.mark.asyncio
async def test_move_character_to_unconnected_location_raises_error():
    """
    Tests that a ValueError is raised if a character tries to move
    to a location that isn't connected to their current one.
    """
    # 1. ARRANGE
    world_repo = InMemoryWorldRepository()
    event_bus = AsyncMock(spec=LocalEventBus)  # Mock the bus, we don't expect it to be called
    mock_memory_service = AsyncMock(spec=MemoryService) # Mock MemoryService
    handler = MoveCharacterHandler(event_bus=event_bus, memory_service=mock_memory_service)

    char_id = CharacterId("player")
    start_loc_id = LocationId("bridge")
    unconnected_loc_id = LocationId("captains_quarters")

    test_world = GameWorld(
        id="test_scenario",
        name="Test Scenario",
        player_id=char_id,
        locations={
            start_loc_id: Location(id=start_loc_id, name="Bridge", description="...", connections=[]),
            unconnected_loc_id: Location(id=unconnected_loc_id, name="Captain's Quarters", description="..."),
        },
        characters={
            char_id: Character(id=char_id, name="Player", description="player description", location_id=start_loc_id) # Added description
        }
    )
    await world_repo.save(test_world)

    command = MoveCharacterCommand(
        world_id="test_scenario",
        character_id=char_id,
        target_location_id=unconnected_loc_id
    )

    # 2. ACT & 3. ASSERT
    with pytest.raises(ValueError, match="not accessible"):
        await handler.execute(command, test_world) # Pass world to execute

    # Assert that the world state was NOT saved and no event was published
    event_bus.publish.assert_not_called()
    mock_memory_service.compress_memory_if_needed.assert_not_called() # Memory service should not be called on error
