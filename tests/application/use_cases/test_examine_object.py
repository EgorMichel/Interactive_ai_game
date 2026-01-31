import pytest
from unittest.mock import AsyncMock

from uin_engine.domain.entities import GameWorld, Character, Location, Fact, Clue, GameObject, CharacterId, LocationId, FactId
from uin_engine.domain.events import FactDiscovered
from uin_engine.infrastructure.repositories.in_memory_world_repository import InMemoryWorldRepository
from uin_engine.infrastructure.event_bus.local_event_bus import LocalEventBus
from uin_engine.application.use_cases.examine_object import ExamineObjectHandler
from uin_engine.application.commands.investigation import ExamineObjectCommand


@pytest.mark.asyncio
async def test_examine_object_discovers_new_clues():
    """
    Tests that examining an object correctly discovers new clues (facts)
    and adds them to the player's knowledge.
    """
    # 1. ARRANGE
    world_repo = InMemoryWorldRepository()
    event_bus = LocalEventBus()
    handler = ExamineObjectHandler(world_repository=world_repo, event_bus=event_bus)

    event_spy = AsyncMock()
    event_bus.subscribe(FactDiscovered, event_spy)

    player_id = CharacterId("player")
    loc_id = LocationId("test_room")
    obj_id = "test_desk"
    fact1_id = FactId("fact_about_desk")
    fact2_id = FactId("fact_about_clue")

    test_fact1 = Fact(id=fact1_id, content="This is a general fact about the desk.")
    test_fact2 = Fact(id=fact2_id, content="This is a specific clue from the desk.")

    test_clue = Clue(fact_id=fact2_id, description="A hidden note.", difficulty=0.5)
    test_object = GameObject(id=obj_id, name="Desk", description="A sturdy wooden desk.", clues=[test_clue])

    test_location = Location(
        id=loc_id,
        name="Test Room",
        description="A simple test room.",
        connections=[],
        objects=[test_object]
    )
    test_player = Character(id=player_id, name="Test Player", description="", location_id=loc_id)

    test_world = GameWorld(
        id="test_world",
        name="Test World",
        player_id=player_id,
        locations={loc_id: test_location},
        characters={player_id: test_player},
        facts={fact1_id: test_fact1, fact2_id: test_fact2}
    )
    await world_repo.save(test_world)

    command = ExamineObjectCommand(
        world_id="test_world",
        player_id=player_id,
        object_id=obj_id,
        location_id=loc_id
    )

    # 2. ACT
    discovered_clues = await handler.execute(command)

    # 3. ASSERT
    # Assert clues were returned
    assert len(discovered_clues) == 1
    assert discovered_clues[0].fact_id == fact2_id
    assert discovered_clues[0].is_found is True # Clue should be marked as found

    # Assert player knowledge was updated
    updated_world = await world_repo.get_by_id("test_world")
    updated_player = updated_world.characters[player_id]
    assert fact2_id in updated_player.knowledge
    assert updated_player.knowledge[fact2_id].certainty == 1.0

    # Assert event was published
    event_spy.assert_called_once()
    published_event: FactDiscovered = event_spy.call_args[0][0]
    assert isinstance(published_event, FactDiscovered)
    assert published_event.character_id == player_id
    assert published_event.fact_id == fact2_id
    assert published_event.location_id == loc_id
    assert published_event.source == f"examining {test_object.name}"


@pytest.mark.asyncio
async def test_examine_object_no_new_clues():
    """
    Tests that examining an object with no new clues results in an empty list
    and no FactDiscovered event.
    """
    # 1. ARRANGE
    world_repo = InMemoryWorldRepository()
    event_bus = LocalEventBus()
    handler = ExamineObjectHandler(world_repository=world_repo, event_bus=event_bus)

    event_spy = AsyncMock()
    event_bus.subscribe(FactDiscovered, event_spy)

    player_id = CharacterId("player")
    loc_id = LocationId("test_room")
    obj_id = "test_desk"

    test_object = GameObject(id=obj_id, name="Desk", description="A sturdy wooden desk.", clues=[]) # No clues
    test_location = Location(
        id=loc_id,
        name="Test Room",
        description="A simple test room.",
        connections=[],
        objects=[test_object]
    )
    test_player = Character(id=player_id, name="Test Player", description="", location_id=loc_id)

    test_world = GameWorld(
        id="test_world",
        name="Test World",
        player_id=player_id,
        locations={loc_id: test_location},
        characters={player_id: test_player},
        facts={}
    )
    await world_repo.save(test_world)

    command = ExamineObjectCommand(
        world_id="test_world",
        player_id=player_id,
        object_id=obj_id,
        location_id=loc_id
    )

    # 2. ACT
    discovered_clues = await handler.execute(command)

    # 3. ASSERT
    assert len(discovered_clues) == 0
    event_spy.assert_not_called()


@pytest.mark.asyncio
async def test_examine_object_already_found_clues():
    """
    Tests that already discovered clues are not re-discovered or re-published.
    """
    # 1. ARRANGE
    world_repo = InMemoryWorldRepository()
    event_bus = LocalEventBus()
    handler = ExamineObjectHandler(world_repository=world_repo, event_bus=event_bus)

    event_spy = AsyncMock()
    event_bus.subscribe(FactDiscovered, event_spy)

    player_id = CharacterId("player")
    loc_id = LocationId("test_room")
    obj_id = "test_desk"
    fact_id = FactId("fact_about_clue")

    test_fact = Fact(id=fact_id, content="This is a specific clue.")
    test_clue = Clue(fact_id=fact_id, description="A hidden note.", difficulty=0.5, is_found=True) # Already found
    test_object = GameObject(id=obj_id, name="Desk", description="A sturdy wooden desk.", clues=[test_clue])

    test_location = Location(
        id=loc_id,
        name="Test Room",
        description="A simple test room.",
        connections=[],
        objects=[test_object]
    )
    test_player = Character(id=player_id, name="Test Player", description="", location_id=loc_id)

    test_world = GameWorld(
        id="test_world",
        name="Test World",
        player_id=player_id,
        locations={loc_id: test_location},
        characters={player_id: test_player},
        facts={fact_id: test_fact}
    )
    await world_repo.save(test_world)

    command = ExamineObjectCommand(
        world_id="test_world",
        player_id=player_id,
        object_id=obj_id,
        location_id=loc_id
    )

    # 2. ACT
    discovered_clues = await handler.execute(command)

    # 3. ASSERT
    assert len(discovered_clues) == 0 # No new clues discovered
    event_spy.assert_not_called() # No new event published

    # Player knowledge should not have been changed by this handler (assuming it was already there)
    updated_world = await world_repo.get_by_id("test_world")
    updated_player = updated_world.characters[player_id]
    assert fact_id not in updated_player.knowledge # Player doesn't get it again if it was already discovered and added

