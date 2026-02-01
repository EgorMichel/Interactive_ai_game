import yaml
from pathlib import Path
from typing import Dict

from uin_engine.domain.scenario_models import ConfigScenario, ConfigObject, ConfigClue
from uin_engine.domain.value_objects import KnowledgeEntry
from uin_engine.domain.entities import GameWorld, Character, Location, Fact, GameObject, Clue, CharacterId, LocationId, FactId, ScheduleEntry, Solution


class ScenarioLoader:
    """
    Loads a game scenario from a YAML file, validates it against Pydantic models,
    and converts it into a GameWorld entity.
    """

    def load_scenario(self, file_path: Path) -> ConfigScenario:
        """
        Loads and validates a scenario configuration from a YAML file.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Scenario file not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f)

        # Validate the raw config against our Pydantic model
        config = ConfigScenario(**raw_config)
        return config

    def convert_to_game_world(self, config: ConfigScenario) -> GameWorld:
        """
        Converts a validated ConfigScenario into a GameWorld entity.
        """
        # Convert facts
        facts_dict: Dict[FactId, Fact] = {fact.id: Fact(**fact.model_dump()) for fact in config.facts}

        # Convert locations
        locations_dict: Dict[LocationId, Location] = {}
        for loc_config in config.locations:
            game_objects: List[GameObject] = []
            for obj_config in loc_config.objects:
                clues: List[Clue] = []
                for clue_config in obj_config.clues:
                    if clue_config.fact_id not in facts_dict:
                        print(f"Warning: Clue fact '{clue_config.fact_id}' for object '{obj_config.id}' in location '{loc_config.id}' not found in scenario facts. Skipping clue.")
                        continue
                    clues.append(Clue(**clue_config.model_dump()))
                game_objects.append(GameObject(
                    id=obj_config.id,
                    name=obj_config.name,
                    description=obj_config.description,
                    clues=clues,
                ))
            
            locations_dict[loc_config.id] = Location(
                id=loc_config.id,
                name=loc_config.name,
                description=loc_config.description,
                connections=loc_config.connections,
                properties=loc_config.properties,
                objects=game_objects,
            )

        # Convert characters
        characters_dict: Dict[CharacterId, Character] = {}
        for char_config in config.characters:
            initial_knowledge: Dict[FactId, KnowledgeEntry] = {}
            for fact_id, certainty in char_config.initial_knowledge.items(): # Changed to .items()
                if fact_id not in facts_dict:
                    print(f"Warning: Fact '{fact_id}' not found for character '{char_config.id}'. Skipping.")
                    continue
                initial_knowledge[fact_id] = KnowledgeEntry(fact_id=fact_id, certainty=certainty) # Use certainty from config

            schedule = [ScheduleEntry(**entry.model_dump()) for entry in char_config.schedule]

            characters_dict[char_config.id] = Character(
                id=char_config.id,
                name=char_config.name,
                description=char_config.description,
                location_id=char_config.initial_location,
                knowledge=initial_knowledge,
                relationships={}, # Will be populated later or from config
                emotional_state={}, # Will be populated later or from config
                goals=char_config.goals,
                schedule=schedule, # Add schedule to Character
            )
        
        # Ensure player character is included if not explicitly in config
        if config.player_id not in characters_dict:
             print(f"Warning: Player character '{config.player_id}' not found in scenario characters. Creating a default player.")
             characters_dict[config.player_id] = Character(
                 id=config.player_id,
                 name="Detective",
                 description="You are a renowned detective.",
                 location_id=config.start_location,
                 goals=["Solve the mystery."],
             )
        else:
            # Update player's starting location from scenario config
            characters_dict[config.player_id].location_id = config.start_location

        game_world = GameWorld(
            id=config.id,
            name=config.name,
            player_id=config.player_id,
            locations=locations_dict,
            characters=characters_dict,
            facts=facts_dict,
        )

        # Convert solution if it exists
        if config.solution:
            game_world.solution = Solution(**config.solution.model_dump())

        return game_world


