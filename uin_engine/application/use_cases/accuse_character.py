from uin_engine.application.ports.world_repository import IWorldRepository
from uin_engine.application.commands.investigation import AccuseCharacterCommand
from uin_engine.domain.entities import GameWorld

class AccusationResult:
    def __init__(self, is_correct: bool, message: str):
        self.is_correct = is_correct
        self.message = message

class AccuseCharacterHandler:
    """
    Handles the AccuseCharacterCommand use case.
    Determines if the player's accusation is correct.
    """
    def __init__(self, world_repository: IWorldRepository):
        self._repo = world_repository

    async def execute(self, command: AccuseCharacterCommand) -> AccusationResult:
        """
        Executes the accusation logic.
        1. Fetches world and player state.
        2. Checks if the scenario has a solution defined.
        3. Checks if the accused character is the killer.
        4. Checks if the player has collected all required facts.
        5. Returns a result object indicating success or failure.
        """
        world = await self._repo.get_by_id(command.world_id)
        if not world:
            raise ValueError(f"World with id '{command.world_id}' not found.")

        player = world.characters.get(command.player_id)
        if not player:
            raise ValueError(f"Player with id '{command.player_id}' not found.")
        
        accused = world.characters.get(command.accused_character_id)
        if not accused:
            raise ValueError(f"Accused character with id '{command.accused_character_id}' not found.")

        if not world.solution:
            return AccusationResult(is_correct=False, message="This mystery has no defined solution. The game continues...")

        # Check 1: Is the accused person the killer?
        is_killer_correct = world.solution.killer_id == command.accused_character_id
        if not is_killer_correct:
            return AccusationResult(
                is_correct=False, 
                message=f"You accuse {accused.name}, but you are wrong. The real killer has gotten away. You lose."
            )

        # Check 2: Does the player have all the required evidence?
        player_known_facts = set(player.knowledge.keys())
        required_facts = set(world.solution.required_fact_ids)
        
        has_all_facts = required_facts.issubset(player_known_facts)

        if not has_all_facts:
            missing_facts = required_facts - player_known_facts
            return AccusationResult(
                is_correct=False,
                message=f"You correctly identified {accused.name} as the killer, but you lack the evidence to prove it! "
                        f"You needed to find {len(missing_facts)} more piece(s) of evidence. The case is dismissed. You lose."
            )

        # If both checks pass, the player wins.
        return AccusationResult(
            is_correct=True,
            message=f"You confront {accused.name} with the evidence. They confess to everything! You have solved the case. You win!"
        )
