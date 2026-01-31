import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from uin_engine.application.services.memory_service import MemoryService
from uin_engine.domain.entities import GameWorld, Character, CharacterId

@pytest.fixture
def setup():
    """Sets up mocks and the service for testing."""
    llm_service = AsyncMock()
    llm_service.summarize.return_value = "This is a summary."

    world_repo = AsyncMock()
    
    memory_service = MemoryService(
        llm_service=llm_service,
        world_repository=world_repo
    )

    world = GameWorld(id="test_world", name="Test", player_id="player")
    char = Character(id="test_char", name="Tester", description="A test character", location_id="test_loc")
    world.characters[char.id] = char
    
    return {
        "llm": llm_service,
        "repo": world_repo,
        "service": memory_service,
        "world": world,
        "char": char
    }

@pytest.mark.asyncio
@patch('asyncio.create_task')
async def test_compress_memory_if_needed_schedules_task_when_threshold_exceeded(mock_create_task, setup):
    """
    Tests that the background task is scheduled ONLY when memory exceeds the threshold.
    """
    # ARRANGE
    service = setup["service"]
    world = setup["world"]
    char = setup["char"]
    
    # Case 1: Memory NOT over threshold
    char.narrative_memory = ["event"] * 10
    service.compress_memory_if_needed(world, char, threshold=15)
    mock_create_task.assert_not_called()

    # Case 2: Memory IS over threshold
    char.narrative_memory = ["event"] * 20
    service.compress_memory_if_needed(world, char, threshold=15)
    mock_create_task.assert_called_once()


@pytest.mark.asyncio
async def test_summarize_chunk_internal_logic(setup):
    """
    Tests the internal _summarize_chunk method directly to verify its logic.
    """
    # ARRANGE
    service = setup["service"]
    llm = setup["llm"]
    repo = setup["repo"]
    world = setup["world"]
    char = setup["char"]

    # Populate memory and define the chunk to be summarized
    char.narrative_memory = [f"event_{i}" for i in range(20)]
    chunk = char.narrative_memory[:10]
    
    # Since the background task fetches the world again, we need to make sure the repo mock returns it
    repo.get_by_id.return_value = world

    # ACT
    # We call the "private" method directly for this unit test
    await service._summarize_chunk(world.id, char.id, chunk)

    # ASSERT
    # 1. Assert that the LLM was called with the correct text
    llm.summarize.assert_awaited_once()
    text_to_summarize = "\n".join(chunk)
    llm.summarize.assert_awaited_with(text_to_summarize)

    # 2. Assert that the character's memory was correctly updated
    # New memory should be [summary] + a_slice_of_the_old_memory
    assert len(char.narrative_memory) == 11 # 1 summary + 10 remaining events
    assert char.narrative_memory[0] == "This is a summary."
    assert char.narrative_memory[1] == "event_10" # The first event after the summarized chunk

    # 3. Assert that the repository was called to save the new world state
    repo.save.assert_awaited_once_with(world)
