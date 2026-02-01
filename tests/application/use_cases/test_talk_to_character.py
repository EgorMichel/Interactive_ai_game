import pytest
from unittest.mock import AsyncMock

from uin_engine.domain.entities import GameWorld, Character, Location, CharacterId, LocationId, Fact
from uin_engine.domain.events import DialogueOccurred
from uin_engine.domain.value_objects import KnowledgeEntry
from uin_engine.infrastructure.repositories.in_memory_world_repository import InMemoryWorldRepository
from uin_engine.infrastructure.event_bus.local_event_bus import LocalEventBus
from uin_engine.infrastructure.llm.mock_llm_service import MockLLMService
from uin_engine.application.use_cases.talk_to_character import TalkToCharacterHandler
from uin_engine.application.commands.dialogue import TalkToCharacterCommand
from uin_engine.application.services.memory_service import MemoryService # Import MemoryService

@pytest.fixture
def setup():
    """Fixture to set up the common test environment."""
    world_repo = InMemoryWorldRepository()
    event_bus = LocalEventBus()
    llm_service = MockLLMService()
    mock_memory_service = AsyncMock(spec=MemoryService) # Mock MemoryService
    handler = TalkToCharacterHandler(
        event_bus=event_bus,
        llm_service=llm_service,
        memory_service=mock_memory_service,
    )
    
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
            player_id: Character(id=player_id, name="Detective", description="A keen observer.", location_id=loc_id),
            npc_id: Character(id=npc_id, name="Sophie", description="A nervous artist.", location_id=loc_id),
        },
        facts={
            "bloody_knife": Fact(id="bloody_knife", content="A bloody knife was found.")
        }
    )
    
    return {
        "repo": world_repo,
        "bus": event_bus,
        "llm": llm_service,
        "handler": handler,
        "world": test_world,
        "player_id": player_id,
        "npc_id": npc_id,
        "mock_memory_service": mock_memory_service # Return mock
    }


@pytest.mark.asyncio
async def test_talk_to_character_successfully(setup):
    """
    Tests the happy path for the dialogue use case.
    Verifies that a dialogue response is generated and an event is published.
    """
    # ARRANGE
    # For this test, ensure the mock LLM does not reveal a fact
    setup["llm"].canned_response_text = "This is a simple response."
    await setup["repo"].save(setup["world"])
    event_spy = AsyncMock()
    setup["bus"].subscribe(DialogueOccurred, event_spy)
    
    command = TalkToCharacterCommand(
        world_id="test_scenario",
        speaker_id=setup["player_id"],
        listener_id=setup["npc_id"],
        message="the strange vial"
    )

    # ACT
    response, world = await setup["handler"].execute(command, setup["world"]) # Pass world
    
    # ASSERT
    assert response.text == "This is a simple response."
    event_spy.assert_called_once()
    published_event: DialogueOccurred = event_spy.call_args[0][0]
    assert isinstance(published_event, DialogueOccurred)
    assert published_event.speaker_id == setup["player_id"]
    assert not published_event.revealed_fact_ids  # No facts should be revealed
    setup["mock_memory_service"].compress_memory_if_needed.assert_called() # Memory service should be called


@pytest.mark.asyncio
async def test_talk_to_character_populates_narrative_memory(setup):
    """
    Tests that dialogue correctly populates the narrative_memory of both participants
    WITHOUT revealing new facts.
    """
    # ARRANGE
    # Ensure the mock service returns a simple response with no fact tags
    setup["llm"].canned_response_text = "Just a regular chat."
    await setup["repo"].save(setup["world"])
    
    command = TalkToCharacterCommand(
        world_id="test_scenario",
        speaker_id=setup["player_id"],
        listener_id=setup["npc_id"],
        message="about the incident"
    )

    # ACT
    response, world = await setup["handler"].execute(command, setup["world"]) # Pass world
    
    # ASSERT
    speaker = world.characters[setup["player_id"]]
    listener = world.characters[setup["npc_id"]]

    # Only two entries per character: one for the prompt, one for the response.
    assert len(speaker.narrative_memory) == 2
    assert len(listener.narrative_memory) == 2

    # Check speaker's memory
    assert f'I said to {listener.name}: "{command.message}"' in speaker.narrative_memory[0]
    assert f'{listener.name} replied to me: "{response.text}"' in speaker.narrative_memory[1]
    
    # Check listener's memory
    assert f'{speaker.name} said to me: "{command.message}"' in listener.narrative_memory[0]
    assert f'I replied to {speaker.name}: "{response.text}"' in listener.narrative_memory[1]
    setup["mock_memory_service"].compress_memory_if_needed.assert_called() # Memory service should be called


@pytest.mark.asyncio
async def test_talk_to_character_reveals_and_adds_fact(setup):
    """
    Tests the full loop of fact extraction: the LLM reveals a fact via a tag,
    and the handler adds it to the character's knowledge.
    """
    # ARRANGE
    # Configure the mock to reveal the 'bloody_knife' fact
    setup["llm"].canned_response_text = "I saw something terrible... a [FACT_REVEALED: bloody_knife] was there."
    await setup["repo"].save(setup["world"])
    
    player = setup["world"].characters[setup["player_id"]]
    assert "bloody_knife" not in player.knowledge  # Pre-condition

    command = TalkToCharacterCommand(
        world_id="test_scenario",
        speaker_id=setup["player_id"],
        listener_id=setup["npc_id"],
        message="what did you see"
    )

    # ACT
    response, world = await setup["handler"].execute(command, setup["world"]) # Pass world

    # ASSERT
    updated_player = world.characters[setup["player_id"]]
    
    # 1. Assert the DTO from the handler is correct
    assert "bloody_knife" in response.newly_revealed_facts
    assert "I saw something terrible" in response.text
    assert "[FACT_REVEALED" not in response.text # Text should be cleaned
    
    # 2. Assert the player's semantic memory (knowledge) was updated
    assert "bloody_knife" in updated_player.knowledge
    assert isinstance(updated_player.knowledge["bloody_knife"], KnowledgeEntry)

    # 3. Assert the player's episodic memory recorded all events in the correct order
    # Total of 3 entries: said, listener replied, learned fact
    assert len(updated_player.narrative_memory) == 3
    assert "I said to Sophie" in updated_player.narrative_memory[0]
    assert "Sophie replied to me" in updated_player.narrative_memory[1]
    assert "I learned something new" in updated_player.narrative_memory[2]
    assert "A bloody knife was found" in updated_player.narrative_memory[2]
    setup["mock_memory_service"].compress_memory_if_needed.assert_called() # Memory service should be called
