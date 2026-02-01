import asyncio
from datetime import time, timedelta, datetime

from pathlib import Path

from uin_engine.container import container
from uin_engine.domain.entities import GameWorld, Character, Location, CharacterId, LocationId, Fact
from uin_engine.application.commands.character import MoveCharacterCommand
from uin_engine.application.commands.dialogue import TalkToCharacterCommand
from uin_engine.application.commands.investigation import ExamineObjectCommand, AccuseCharacterCommand
from uin_engine.infrastructure.config.scenario_loader import ScenarioLoader
from uin_engine.application.services.npc_behavior_system import GAME_TIME_INCREMENT_MINUTES

# --- Constants for our demo ---
WORLD_ID = "yacht_mystery"
PLAYER_ID = CharacterId("player")
SCENARIO_FILE = Path("scenarios/yacht_mystery.yaml")


async def _setup_demo_world():
    """Loads the world state from a scenario file and saves it to the repository."""
    repo = container.world_repository()
    scenario_loader = container.scenario_loader()
    config_scenario = scenario_loader.load_scenario(SCENARIO_FILE)
    world = scenario_loader.convert_to_game_world(config_scenario)
    await repo.save(world)
    print(f"Demo world '{world.name}' loaded from {SCENARIO_FILE}.")


async def main():
    """The main game loop for the CLI."""
    await _setup_demo_world()
    
    repo = container.world_repository()
    move_handler = container.move_character_handler()
    talk_handler = container.talk_to_character_handler()
    examine_handler = container.examine_object_handler()
    accuse_handler = container.accuse_character_handler()
    npc_behavior_system = container.npc_behavior_system()

    print("\n--- UIN Engine ---")
    print("Welcome to 'The Nereid Yacht Mystery'.")
    print("Available commands: 'look', 'move <location>', 'talk <character> <message>', 'examine <object>', 'accuse <character>', 'quit'")

    while True:
        try:
            # Load the current world state at the beginning of each turn
            world = await repo.get_by_id(WORLD_ID)

            # --- Describe the current situation ---
            player = world.characters[PLAYER_ID]
            current_location = world.locations[player.location_id]

            print("\n" + "="*40)
            print(f"Game Time: {world.game_time.strftime('%H:%M')}")
            print(f"You are on the {current_location.name}.")
            print(current_location.description)

            if current_location.objects:
                print(f"You see the following objects: {', '.join([obj.name for obj in current_location.objects])}")
            
            other_chars = [c for c in world.characters.values() if c.location_id == current_location.id and c.id != PLAYER_ID]
            if other_chars:
                print(f"You see: {', '.join([c.name for c in other_chars])}")
            
            print(f"Exits: {', '.join(current_location.connections)}")
            
            # --- Get and process user input ---
            command_str = input("> ").strip().lower()
            parts = command_str.split()
            if not parts:
                continue

            verb = parts[0]
            action_succeeded = False

            if verb == "quit":
                print("Goodbye!")
                break
            
            elif verb == "look":
                # Looking doesn't advance time, but we mark it as "successful" to avoid error messages
                # The time advancement logic is skipped because no state is saved.
                # To make 'look' advance time, set action_succeeded = True
                continue

            elif verb == "move":
                if len(parts) < 2:
                    print("Move where? 'move <location>'")
                else:
                    target_loc_name = " ".join(parts[1:])
                    target_loc_id = next((loc.id for loc in world.locations.values() if loc.name.lower() == target_loc_name), None)
                    if not target_loc_id:
                        print(f"Location '{target_loc_name}' not found.")
                    else:
                        command = MoveCharacterCommand(world_id=WORLD_ID, character_id=PLAYER_ID, target_location_id=target_loc_id)
                        world = await move_handler.execute(command, world)
                        print(f"You move to the {target_loc_name}.")
                        action_succeeded = True
            
            elif verb == "talk":
                if len(parts) < 3:
                    print("Talk to who and about what? 'talk <character> <message>'")
                else:
                    target_char_name = parts[1]
                    message = " ".join(parts[2:])
                    target_char = next((c for c in other_chars if c.name.lower() == target_char_name), None)
                    if not target_char:
                        print(f"Character '{target_char_name}' not found here.")
                    else:
                        command = TalkToCharacterCommand(world_id=WORLD_ID, speaker_id=PLAYER_ID, listener_id=target_char.id, message=message)
                        response, world = await talk_handler.execute(command, world)
                        print(f"{target_char.name}: \"{response.text}\"")
                        action_succeeded = True

            elif verb == "examine":
                if len(parts) < 2:
                    print("Examine what? 'examine <object>'")
                else:
                    target_obj_name = " ".join(parts[1:])
                    target_object = next((obj for obj in current_location.objects if obj.name.lower() == target_obj_name), None)
                    if not target_object:
                        print(f"Object '{target_obj_name}' not found in {current_location.name}.")
                    else:
                        command = ExamineObjectCommand(world_id=WORLD_ID, player_id=PLAYER_ID, object_id=target_object.id, location_id=current_location.id)
                        discovered_clues, world = await examine_handler.execute(command, world)
                        if not discovered_clues:
                            print(f"You examine the {target_obj_name} carefully, but find nothing new.")
                        action_succeeded = True
            
            elif verb == "accuse":
                if len(parts) < 2:
                    print("Accuse who? 'accuse <character>'")
                else:
                    accused_name = " ".join(parts[1:])
                    accused_char = next((c for c in world.characters.values() if c.name.lower() == accused_name), None)
                    if not accused_char:
                        print(f"Character '{accused_name}' not found in the world.")
                    else:
                        command = AccuseCharacterCommand(world_id=WORLD_ID, player_id=PLAYER_ID, accused_character_id=accused_char.id)
                        result = await accuse_handler.execute(command)
                        print("\n" + "*"*10 + " The End " + "*"*10)
                        print(result.message)
                        print("*"*29)
                        break # End the game

            else:
                print(f"Unknown command: '{verb}'")

            # --- Game State Update (only if player action was valid and changed state) ---
            if action_succeeded:
                world = await npc_behavior_system.update_game_time(world)
                world = await npc_behavior_system.execute_npc_behaviors(world)
                await repo.save(world) # Save the final state of the world for this turn

        except Exception as e:
            print(f"ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
