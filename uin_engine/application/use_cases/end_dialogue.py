from uin_engine.application.ports.event_bus import IEventBus
from uin_engine.application.services.memory_service import MemoryService
from uin_engine.application.commands.dialogue import EndDialogueCommand
from uin_engine.domain.entities import GameWorld

class EndDialogueHandler:
    """
    Handles the command to end a dialogue session and summarize it into
    the participants' long-term narrative memory.
    """
    def __init__(self, memory_service: MemoryService, event_bus: IEventBus):
        self._memory_service = memory_service
        self._bus = event_bus

    async def execute(self, command: EndDialogueCommand, world: GameWorld) -> GameWorld:
        """
        1. Finds the dialogue session.
        2. If found, summarizes its history for each participant.
        3. Deactivates or removes the session.
        4. Returns the updated world.
        """
        session = world.active_dialogues.get(command.session_id)
        if not session or not session.is_active:
            # Session might have already ended, which is not an error.
            return world

        # Summarize the dialogue for each participant's memory
        if session.history:
            for participant_id in session.participants:
                character = world.characters.get(participant_id)
                if character:
                    # We summarize the entire session history by passing a start_index of 0
                    # relative to the session's history, not the character's main memory.
                    dialogue_replicas = [f"{world.characters[r.speaker_id].name}: \"{r.message}\"" for r in session.history]
                    await self._memory_service.summarize_and_add_to_memory(character, dialogue_replicas)

        # Mark the session as inactive
        session.is_active = False
        # Or simply remove it:
        del world.active_dialogues[command.session_id]

        # Note: Time advancement is handled by the main loop after this handler is called.

        return world
