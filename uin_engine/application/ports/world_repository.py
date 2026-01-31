from abc import ABC, abstractmethod
from typing import Optional

from uin_engine.domain.entities import GameWorld


class IWorldRepository(ABC):
    """
    An interface (Port) for persisting and retrieving the game world state.
    This contract is defined by the application layer and implemented by
    the infrastructure layer.
    """

    @abstractmethod
    async def get_by_id(self, world_id: str) -> Optional[GameWorld]:
        """
        Retrieves a complete game world aggregate by its unique ID.
        Returns None if the world is not found.
        """
        pass

    @abstractmethod
    async def save(self, world: GameWorld) -> None:
        """
        Saves the entire state of the game world aggregate.
        This should handle both creation and updates.
        """
        pass
