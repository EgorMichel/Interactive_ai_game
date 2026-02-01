import pytest
from uin_engine.application.use_cases.accuse_character import AccuseCharacterHandler
from uin_engine.application.commands.investigation import AccuseCharacterCommand
from uin_engine.domain.entities import GameWorld, Character, Solution, FactId, CharacterId
from uin_engine.domain.value_objects import KnowledgeEntry
from uin_engine.infrastructure.repositories.in_memory_world_repository import InMemoryWorldRepository

# --- Test Fixtures ---

@pytest.fixture
def solved_world():
    """A fixture for a GameWorld with a defined solution."""
    solution = Solution(killer_id="sophie", required_fact_ids=["fact1", "fact2"])
    player = Character(id="player", name="Player", description="A player", location_id="bridge", knowledge={})
    sophie = Character(id="sophie", name="Sophie", description="A suspect", location_id="deck")
    mark = Character(id="mark", name="Mark", description="Another suspect", location_id="bridge")

    return GameWorld(
        id="test_world",
        name="Test World",
        player_id="player",
        solution=solution,
        characters={"player": player, "sophie": sophie, "mark": mark}
    )

# --- Test Cases ---

@pytest.mark.asyncio
async def test_accuse_correctly_with_all_facts(solved_world):
    """
    Scenario: Player accuses the correct killer and has all required facts.
    Expected: Win condition (is_correct = True).
    """
    # Arrange
    repo = InMemoryWorldRepository()
    player = solved_world.characters["player"]
    player.knowledge = {
        "fact1": KnowledgeEntry(fact_id="fact1", certainty=1.0),
        "fact2": KnowledgeEntry(fact_id="fact2", certainty=1.0),
        "fact3": KnowledgeEntry(fact_id="fact3", certainty=1.0), # Extra fact
    }
    await repo.save(solved_world)
    
    handler = AccuseCharacterHandler(world_repository=repo)
    command = AccuseCharacterCommand(world_id="test_world", player_id="player", accused_character_id="sophie")

    # Act
    result = await handler.execute(command)

    # Assert
    assert result.is_correct is True
    assert "You win!" in result.message

@pytest.mark.asyncio
async def test_accuse_incorrect_person(solved_world):
    """
    Scenario: Player accuses the wrong person.
    Expected: Lose condition (is_correct = False).
    """
    # Arrange
    repo = InMemoryWorldRepository()
    player = solved_world.characters["player"]
    player.knowledge = {
        "fact1": KnowledgeEntry(fact_id="fact1", certainty=1.0),
        "fact2": KnowledgeEntry(fact_id="fact2", certainty=1.0),
    }
    await repo.save(solved_world)
    
    handler = AccuseCharacterHandler(world_repository=repo)
    command = AccuseCharacterCommand(world_id="test_world", player_id="player", accused_character_id="mark")

    # Act
    result = await handler.execute(command)

    # Assert
    assert result.is_correct is False
    assert "You lose." in result.message
    assert "you are wrong" in result.message

@pytest.mark.asyncio
async def test_accuse_correctly_with_missing_facts(solved_world):
    """
    Scenario: Player accuses the correct killer but lacks required evidence.
    Expected: Lose condition (is_correct = False).
    """
    # Arrange
    repo = InMemoryWorldRepository()
    player = solved_world.characters["player"]
    # Player only has one of the two required facts
    player.knowledge = {"fact1": KnowledgeEntry(fact_id="fact1", certainty=1.0)}
    await repo.save(solved_world)
    
    handler = AccuseCharacterHandler(world_repository=repo)
    command = AccuseCharacterCommand(world_id="test_world", player_id="player", accused_character_id="sophie")

    # Act
    result = await handler.execute(command)

    # Assert
    assert result.is_correct is False
    assert "You lose." in result.message
    assert "you lack the evidence" in result.message

@pytest.mark.asyncio
async def test_accuse_in_scenario_with_no_solution(solved_world):
    """
    Scenario: Player tries to accuse someone in a world without a solution.
    Expected: A neutral message, game continues (is_correct = False).
    """
    # Arrange
    repo = InMemoryWorldRepository()
    solved_world.solution = None # Remove the solution
    await repo.save(solved_world)
    
    handler = AccuseCharacterHandler(world_repository=repo)
    command = AccuseCharacterCommand(world_id="test_world", player_id="player", accused_character_id="sophie")

    # Act
    result = await handler.execute(command)

    # Assert
    assert result.is_correct is False
    assert "no defined solution" in result.message
