import asyncio
from typing import Optional

from pathlib import Path

from uin_engine.container import container
from uin_engine.domain.entities import CharacterId
from uin_engine.application.commands.character import MoveCharacterCommand
from uin_engine.application.commands.dialogue import TalkToCharacterCommand
from uin_engine.application.commands.investigation import ExamineObjectCommand, AccuseCharacterCommand

# --- Constants for our demo ---
WORLD_ID = "yacht_mystery"
PLAYER_ID = CharacterId("player")
SCENARIO_FILE = Path("scenarios/yacht_mystery.yaml")

# --- Command definitions ---
COMMANDS = ["look", "move", "talk", "examine", "accuse", "quit", "help", "goodbye"]

async def _setup_demo_world():
    """Loads the world state from a scenario file and saves it to the repository."""
    repo = container.world_repository()
    scenario_loader = container.scenario_loader()
    config_scenario = scenario_loader.load_scenario(SCENARIO_FILE)
    world = scenario_loader.convert_to_game_world(config_scenario)
    await repo.save(world)
    print(f"Demo world '{world.name}' loaded from {SCENARIO_FILE}.")

def print_help():
    """Prints the available commands."""
    print("\n--- Help ---")
    print("Available commands:")
    print("  look                            - Look around your current location.")
    print("  move <location_name>            - Move to a new location.")
    print("  talk <character_name> <message> - Start or continue a conversation.")
    print("  <message>                       - Continue conversation with the last person you talked to.")
    print("  examine <object_name>           - Examine an object in your location.")
    print("  accuse <character_name>         - Accuse a character of the crime (ends the game).")
    print("  goodbye                         - End the current conversation.")
    print("  quit                            - Exit the game.")
    print("---")


async def main():
    """The main game loop for the CLI, with dialogue context."""
    await _setup_demo_world()
    
    repo = container.world_repository()
    move_handler = container.move_character_handler()
    talk_handler = container.talk_to_character_handler()
    examine_handler = container.examine_object_handler()
    accuse_handler = container.accuse_character_handler()
    npc_behavior_system = container.npc_behavior_system()

    print("\n--- UIN Engine ---")
    print("Welcome to 'The Nereid Yacht Mystery'. Type 'help' for commands.")
    
    last_interlocutor: Optional[CharacterId] = None

    while True:
        try:
            world = await repo.get_by_id(WORLD_ID)
            player = world.characters[PLAYER_ID]
            current_location = world.locations[player.location_id]
            other_chars = [c for c in world.characters.values() if c.location_id == current_location.id and c.id != PLAYER_ID]

            # --- Print current situation (only if not in a continuous dialogue) ---
            if last_interlocutor:
                listener_name = world.characters.get(last_interlocutor, "Unknown").name
                prompt = f"(talking to {listener_name})> "
            else:
                print("\n" + "="*40)
                print(f"Game Time: {world.game_time.strftime('%H:%M')}")
                print(f"You are on the {current_location.name}.")
                print(current_location.description)

                if current_location.objects:
                    print(f"You see the following objects: {', '.join([obj.name for obj in current_location.objects])}")
                if other_chars:
                    print(f"You see: {', '.join([c.name for c in other_chars])}")
                print(f"Exits: {', '.join(current_location.connections)}")
                prompt = "> "
            
            command_str = input(prompt).strip()
            parts = command_str.split()
            if not parts:
                continue

            verb = parts[0].lower()
            action_succeeded = False
            
            # --- Command Parsing ---
            if verb == "quit":
                print("Goodbye!")
                break
            
            elif verb == "help":
                print_help()
                continue

            elif verb not in COMMANDS:
                # --- Implicit Dialogue Continuation ---
                if last_interlocutor:
                    target_char = world.characters.get(last_interlocutor)
                    if not target_char or target_char.location_id != player.location_id:
                        print("The person you were talking to is no longer here.")
                        last_interlocutor = None
                        continue
                    
                    message = command_str # The whole input is the message
                    command = TalkToCharacterCommand(world_id=WORLD_ID, speaker_id=PLAYER_ID, listener_id=last_interlocutor, message=message)
                    response, world = await talk_handler.execute(command, world)
                    print(f"{target_char.name}: \"{response.text}\""")
                    action_succeeded = True
                else:
                    print(f"Unknown command: '{verb}'. Type 'help' for a list of commands.")
                    continue

            elif verb == "look":
                last_interlocutor = None
                continue

            elif verb == "goodbye":
                if last_interlocutor:
                    print(f"You end the conversation with {world.characters[last_interlocutor].name}.")
                    last_interlocutor = None
                else:
                    print("You are not talking to anyone.")
                continue

            elif verb == "move":
                last_interlocutor = None
                if len(parts) > 1:
                    target_loc_name = " ".join(parts[1:])
                    target_loc_id = next((loc.id for loc in world.locations.values() if loc.name.lower() == target_loc_name), None)
                    if target_loc_id:
                        command = MoveCharacterCommand(world_id=WORLD_ID, character_id=PLAYER_ID, target_location_id=target_loc_id)
                        world = await move_handler.execute(command, world)
                        print(f"You move to the {target_loc_name}.")
                        action_succeeded = True
                    else:
                        print(f"Location '{target_loc_name}' not found.")
                else:
                    print("Move where? 'move <location>'"")

            elif verb == "talk":
                if len(parts) > 2:
                    target_char_name = parts[1]
                    message = " ".join(parts[2:])
                    target_char = next((c for c in other_chars if c.name.lower() == target_char_name), None)
                    if target_char:
                        last_interlocutor = target_char.id # Set dialogue context
                        command = TalkToCharacterCommand(world_id=WORLD_ID, speaker_id=PLAYER_ID, listener_id=target_char.id, message=message)
                        response, world = await talk_handler.execute(command, world)
                        print(f"{target_char.name}: \"{response.text}\""")
                        action_succeeded = True
                    else:
                        print(f"Character '{target_char_name}' not found here.")
                else:
                    print("Talk to who and about what? 'talk <character> <message>'"")
            
            elif verb == "examine":
                last_interlocutor = None
                if len(parts) > 1:
                    target_obj_name = " ".join(parts[1:])
                    target_object = next((obj for obj in current_location.objects if obj.name.lower() == target_obj_name), None)
                    if target_object:
                        command = ExamineObjectCommand(world_id=WORLD_ID, player_id=PLAYER_ID, object_id=target_object.id, location_id=current_location.id)
                        discovered_clues, world = await examine_handler.execute(command, world)
                        if not discovered_clues:
                            print(f"You examine the {target_obj_name} carefully, but find nothing new.")
                        action_succeeded = True
                    else:
                        print(f"Object '{target_obj_name}' not found in {current_location.name}.")
                else:
                    print("Examine what? 'examine <object>'"")

            elif verb == "accuse":
                last_interlocutor = None
                if len(parts) > 1:
                    accused_name = " ".join(parts[1:])
                    accused_char = next((c for c in world.characters.values() if c.name.lower() == accused_name), None)
                    if accused_char:
                        command = AccuseCharacterCommand(world_id=WORLD_ID, player_id=PLAYER_ID, accused_character_id=accused_char.id)
                        result = await accuse_handler.execute(command)
                        print("\n" + "*"*10 + " The End " + "*"*10)
                        print(result.message)
                        print("*"*29)
                        break
                    else:
                        print(f"Character '{accused_name}' not found in the world.")
                else:
                    print("Accuse who? 'accuse <character>'"")
            
            # --- Game State Update ---
            if action_succeeded:
                world = await npc_behavior_system.update_game_time(world)
                world = await npc_behavior_system.execute_npc_behaviors(world)
                await repo.save(world)

        except Exception as e:
            print(f"ERROR: An unexpected error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())