import asyncio
from typing import Optional

from pathlib import Path

from uin_engine.container import container, wire_dependencies
from uin_engine.domain.entities import CharacterId, DialogueSessionId
from uin_engine.application.commands.character import MoveCharacterCommand
from uin_engine.application.commands.dialogue import TalkToCharacterCommand, EndDialogueCommand
from uin_engine.application.commands.investigation import ExamineObjectCommand, AccuseCharacterCommand

# --- Constants ---
WORLD_ID = "yacht_mystery"
PLAYER_ID = CharacterId("player")
SCENARIO_FILE = Path("scenarios/yacht_mystery.yaml")
COMMANDS = ["look", "move", "talk", "examine", "accuse", "quit", "help", "goodbye"]

async def _setup_demo_world():
    """Loads the world state from a scenario file."""
    repo = container.world_repository()
    scenario_loader = container.scenario_loader()
    config_scenario = scenario_loader.load_scenario(SCENARIO_FILE)
    world = scenario_loader.convert_to_game_world(config_scenario)
    await repo.save(world)
    print(f"Demo world '{world.name}' loaded from {SCENARIO_FILE}.")

def print_help():
    """Prints available commands."""
    print("\n--- Help ---")
    print("  look                            - See your surroundings.")
    print("  move <location>                 - Move to a new location.")
    print("  talk <character> <message>      - Start a conversation.")
    print("  <message>                       - Continue the current conversation.")
    print("  goodbye                         - End the current conversation.")
    print("  examine <object>                - Examine an object.")
    print("  accuse <character>              - Accuse a character (ends the game).")
    print("  quit                            - Exit the game.")
    print("---")


async def main():
    """The main game loop, now with dialogue session management."""
    wire_dependencies()
    await _setup_demo_world()
    
    # Resolve handlers from container
    repo = container.world_repository()
    move_handler = container.move_character_handler()
    talk_handler = container.talk_to_character_handler()
    end_dialogue_handler = container.end_dialogue_handler()
    examine_handler = container.examine_object_handler()
    accuse_handler = container.accuse_character_handler()
    npc_behavior_system = container.npc_behavior_system()

    print("\n--- UIN Engine ---")
    print("Welcome to 'The Nereid Yacht Mystery'. Type 'help' for commands.")
    
    player_session_id: Optional[DialogueSessionId] = None

    while True:
        try:
            world = await repo.get_by_id(WORLD_ID)
            player = world.characters[PLAYER_ID]
            current_location = world.locations[player.location_id]
            
            prompt = "> "
            if player_session_id and player_session_id in world.active_dialogues:
                session = world.active_dialogues[player_session_id]
                # Find the other participant
                other_participant_id = next((p for p in session.participants if p != PLAYER_ID), None)
                if other_participant_id:
                    prompt = f"(talking to {world.characters[other_participant_id].name})> "

            else: # Not in a dialogue
                player_session_id = None # Ensure session is cleared if it was closed elsewhere
                print("\n" + "="*40)
                print(f"Game Time: {world.game_time.strftime('%H:%M')}")
                print(f"You are on the {current_location.name}.")
                print(current_location.description)
                
                other_chars = [c for c in world.characters.values() if c.location_id == current_location.id and c.id != PLAYER_ID]
                if current_location.objects:
                    print(f"You see the following objects: {', '.join([obj.name for obj in current_location.objects])}")
                if other_chars:
                    print(f"You see: {', '.join([c.name for c in other_chars])}")
                print(f"Exits: {', '.join(current_location.connections)}")

            command_str = input(prompt).strip()
            parts = command_str.split()
            if not parts:
                continue

            verb = parts[0].lower()
            action_succeeded = False

            # --- Command Parsing ---
            if verb not in COMMANDS:
                if player_session_id:
                    session = world.active_dialogues.get(player_session_id)
                    if not session or not session.is_active:
                        print("Your conversation ended unexpectedly.")
                        player_session_id = None
                        continue
                    
                    listener_id = next((p for p in session.participants if p != PLAYER_ID), None)
                    if not listener_id or world.characters[listener_id].location_id != player.location_id:
                        print("The person you were talking to is no longer here.")
                        player_session_id = None
                        continue

                    message = command_str
                    command = TalkToCharacterCommand(
                        world_id=WORLD_ID, 
                        speaker_id=PLAYER_ID, 
                        listener_id=listener_id,
                        session_id=player_session_id, 
                        message=message
                    )
                    world, _ = await talk_handler.execute(command, world)
                    action_succeeded = True
                else:
                    print(f"Unknown command: '{verb}'. Type 'help' for a list of commands.")
            
            elif verb == "quit":
                print("Goodbye!")
                break
            
            elif verb == "help":
                print_help()
            
            elif verb == "goodbye":
                if player_session_id:
                    command = EndDialogueCommand(world_id=WORLD_ID, session_id=player_session_id)
                    world = await end_dialogue_handler.execute(command, world)
                    print("You end the conversation.")
                    player_session_id = None
                    action_succeeded = True
                else:
                    print("You are not talking to anyone.")

            elif verb == "talk":
                if len(parts) > 2:
                    target_char_name = parts[1]
                    message = " ".join(parts[2:])
                    target_char = next((c for c in world.characters.values() if c.location_id == player.location_id and c.name.lower() == target_char_name.lower()), None)
                    if target_char:
                        command = TalkToCharacterCommand(world_id=WORLD_ID, speaker_id=PLAYER_ID, listener_id=target_char.id, message=message)
                        world, new_session_id = await talk_handler.execute(command, world)
                        player_session_id = new_session_id
                        action_succeeded = True
                    else:
                        print(f"Character '{target_char_name}' not found here.")
                else:
                    print("Usage: talk <character> <message>")

            else: # move, look, examine, accuse
                if player_session_id:
                    # Implicitly end dialogue if another action is taken
                    command = EndDialogueCommand(world_id=WORLD_ID, session_id=player_session_id)
                    world = await end_dialogue_handler.execute(command, world)
                    print(f"You step away from the conversation.")
                    player_session_id = None
                
                if verb == "look":
                    pass 
                
                elif verb == "move":
                    if len(parts) > 1:
                        target_loc_name = " ".join(parts[1:])
                        target_loc_id = next((loc.id for loc in world.locations.values() if loc.name.lower() == target_loc_name.lower()), None)
                        if target_loc_id:
                            command = MoveCharacterCommand(world_id=WORLD_ID, character_id=PLAYER_ID, target_location_id=target_loc_id)
                            world = await move_handler.execute(command, world)
                            print(f"You move to the {target_loc_name}.")
                            action_succeeded = True
                        else:
                            print(f"Location '{target_loc_name}' not found.")
                    else:
                        print("Usage: move <location_name>")

                elif verb == "examine":
                    if len(parts) > 1:
                        target_obj_name = " ".join(parts[1:])
                        target_object = next((obj for obj in current_location.objects if obj.name.lower() == target_obj_name.lower()), None)
                        if target_object:
                            command = ExamineObjectCommand(world_id=WORLD_ID, player_id=PLAYER_ID, object_id=target_object.id, location_id=current_location.id)
                            discovered_clues, world = await examine_handler.execute(command, world)
                            if not discovered_clues:
                                print(f"You examine the {target_obj_name} carefully, but find nothing new.")
                            action_succeeded = True
                        else:
                            print(f"Object '{target_obj_name}' not found here.")
                    else:
                        print("Usage: examine <object_name>")

                elif verb == "accuse":
                    if len(parts) > 1:
                        accused_name = " ".join(parts[1:])
                        accused_char = next((c for c in world.characters.values() if c.name.lower() == accused_name.lower()), None)
                        if accused_char:
                            command = AccuseCharacterCommand(world_id=WORLD_ID, player_id=PLAYER_ID, accused_character_id=accused_char.id)
                            result = await accuse_handler.execute(command)
                            print("\n" + "*"*10 + " The End " + "*"*10)
                            print(result.message)
                            print("*"*29)
                            break
                        else:
                            print(f"Character '{accused_name}' not found.")
                    else:
                        print("Usage: accuse <character_name>")

            # --- Game State Update ---
            if action_succeeded:
                world = await npc_behavior_system.update_game_time(world)
                world = await npc_behavior_system.execute_npc_behaviors(world)
                await repo.save(world)

        except Exception as e:
            print(f"ERROR: An unexpected error occurred: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())