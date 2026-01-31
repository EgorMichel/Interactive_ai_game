from typing import Dict, Optional

from uin_engine.domain.entities import GameWorld
from uin_engine.application.ports.world_repository import IWorldRepository


class InMemoryWorldRepository(IWorldRepository):
    """
    An in-memory implementation of the IWorldRepository.
    It stores the game world state in a simple dictionary.
    Useful for testing and development without a real database.
    """
    _worlds: Dict[str, GameWorld]

    def __init__(self):
        self._worlds = {}

    async def get_by_id(self, world_id: str) -> Optional[GameWorld]:
        """
        Retrieves a game world from the in-memory dictionary.
        Returns a copy to prevent mutation of the stored state.
        """
        world = self._worlds.get(world_id)
        return world.model_copy(deep=True) if world else None

    async def save(self, world: GameWorld) -> None:
        """
        Saves a game world to the in-memory dictionary.
        Stores a copy to ensure the repository owns its state.
        """
        self._worlds[world.id] = world.model_copy(deep=True)

    def clear(self) -> None:
        """A helper method for tests to clear the repository state."""
        self._worlds = {}

