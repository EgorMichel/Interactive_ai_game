from uin_engine.application.ports.world_repository import IWorldRepository
from uin_engine.application.ports.event_bus import IEventBus
from uin_engine.application.ports.llm_service import ILLMService, DialogueGenerationContext, DialogueGenerationResponse
from uin_engine.application.commands.dialogue import TalkToCharacterCommand
from uin_engine.domain.events import DialogueOccurred


from uin_engine.domain.entities import DialogueEntry, GameWorld


class TalkToCharacterHandler:
    """
    Handles the TalkToCharacterCommand use case.
    Orchestrates domain models and infrastructure services to generate a dialogue response.
    """
    def __init__(
        self,
        world_repository: IWorldRepository,
        event_bus: IEventBus,
        llm_service: ILLMService,
    ):
        self._repo = world_repository
        self._bus = event_bus
        self._llm = llm_service

    async def execute(self, command: TalkToCharacterCommand) -> tuple[DialogueGenerationResponse, GameWorld]:
        """
        Executes the dialogue logic.
        1. Fetches state.
        2. Validates domain rules (e.g., location).
        3. Builds context for the LLM, including recent dialogue.
        4. Calls the LLM service.
        5. Updates the world state with the new dialogue.
        6. Publishes an event.
        7. Returns the response and the updated world to the caller.
        """
        world = await self._repo.get_by_id(command.world_id)
        if not world:
            raise ValueError(f"World with id '{command.world_id}' not found.")

        speaker = world.characters.get(command.speaker_id)
        if not speaker:
            raise ValueError(f"Speaker with id '{command.speaker_id}' not found.")

        listener = world.characters.get(command.listener_id)
        if not listener:
            raise ValueError(f"Listener with id '{command.listener_id}' not found.")

        if speaker.location_id != listener.location_id:
            raise ValueError(f"{speaker.name} and {listener.name} are not in the same location.")

        # Build recent dialogue history (short-term memory)
        history_lines = []
        for entry in world.dialogue_history[-10:]: # Look at last 10 entries for context
            if (entry.speaker_id in [speaker.id, listener.id] and 
                entry.listener_id in [speaker.id, listener.id]):
                speaker_name = world.characters[entry.speaker_id].name
                history_lines.append(f"{speaker_name}: {entry.message}")
        recent_history_str = "\n".join(history_lines)

        context = DialogueGenerationContext(
            speaker_name=speaker.name,
            speaker_description=speaker.description,
            speaker_goals=speaker.goals,
            speaker_knowledge="; ".join([f.content for f in world.facts.values() if f.id in speaker.knowledge]),
            listener_name=listener.name,
            listener_description=listener.description,
            listener_goals=listener.goals,
            listener_knowledge="; ".join([f.content for f in world.facts.values() if f.id in listener.knowledge]),
            recent_dialogue_history=recent_history_str,
            current_topic=command.message,
        )

        # Call the external LLM service
        response = await self._llm.generate_dialogue(context)

        # Update world state with new dialogue entries
        world.dialogue_history.append(DialogueEntry(
            speaker_id=speaker.id,
            listener_id=listener.id,
            message=command.message,
            game_time=world.game_time
        ))
        world.dialogue_history.append(DialogueEntry(
            speaker_id=listener.id,
            listener_id=speaker.id,
            message=response.text,
            game_time=world.game_time
        ))

        await self._repo.save(world)

        # Publish an event
        event = DialogueOccurred(
            speaker_id=speaker.id,
            listener_id=listener.id,
            dialogue_text=response.text,
            revealed_fact_ids=[]
        )
        await self._bus.publish(event)

        return response, world

