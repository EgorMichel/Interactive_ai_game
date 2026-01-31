import pytest
from unittest.mock import AsyncMock

from uin_engine.domain.entities import GameWorld, Character, Location, CharacterId, LocationId
from uin_engine.domain.events import DialogueOccurred
from uin_engine.infrastructure.repositories.in_memory_world_repository import InMemoryWorldRepository
from uin_engine.infrastructure.event_bus.local_event_bus import LocalEventBus
from uin_engine.infrastructure.llm.mock_llm_service import MockLLMService
from uin_engine.application.use_cases.talk_to_character import TalkToCharacterHandler
from uin_engine.application.commands.dialogue import TalkToCharacterCommand

@pytest.mark.asyncio
async def test_talk_to_character_successfully():
    """
    Tests the happy path for the dialogue use case.
    Verifies that a dialogue response is generated and an event is published.
    """
    # 1. ARRANGE
    # Setup all dependencies using our in-memory/mock implementations
    world_repo = InMemoryWorldRepository()
    event_bus = LocalEventBus()
    llm_service = MockLLMService()
    handler = TalkToCharacterHandler(
        world_repository=world_repo,
        event_bus=event_bus,
        llm_service=llm_service
    )

    # Create a "spy" to watch the event bus for a specific event
    event_spy = AsyncMock()
    event_bus.subscribe(DialogueOccurred, event_spy)

    # Prepare the initial state of the world
    player_id = CharacterId("player")
    npc_id = CharacterId("sophie")
    loc_id = LocationId("library")
    test_world = GameWorld(
        id="test_scenario",
        name="Test Scenario",
        player_id=player_id,
        locations={
            loc_id: Location(id=loc_id, name="Library", description="A quiet room with books.", connections=[])
        },
        characters={
            player_id: Character(id=player_id, name="Detective", description="A keen observer.", location_id=loc_id, goals=[]),
            npc_id: Character(id=npc_id, name="Sophie", description="A nervous artist.", location_id=loc_id, goals=[]),
        }
    )
    await world_repo.save(test_world)

    command = TalkToCharacterCommand(
        world_id="test_scenario",
        speaker_id=player_id,
        listener_id=npc_id,
        message="the strange vial"
    )

    # 2. ACT
    response = await handler.execute(command)

    # 3. ASSERT
    # Assert the response DTO returned by the handler is correct
    assert "My name is Sophie" in response.text
    assert f"asked me about '{command.message}'" in response.text

    # Assert our spy caught the event
    event_spy.assert_called_once()
    
    # Assert the content of the published event is correct
    published_event: DialogueOccurred = event_spy.call_args[0][0]
    assert isinstance(published_event, DialogueOccurred)
    assert published_event.speaker_id == player_id
    assert published_event.listener_id == npc_id
    assert f"asked me about '{command.message}'" in published_event.dialogue_text
