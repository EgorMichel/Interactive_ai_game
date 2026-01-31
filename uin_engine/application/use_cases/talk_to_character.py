from uin_engine.application.ports.world_repository import IWorldRepository
from uin_engine.application.ports.event_bus import IEventBus
from uin_engine.application.ports.llm_service import ILLMService, DialogueGenerationContext, DialogueGenerationResponse
from uin_engine.application.commands.dialogue import TalkToCharacterCommand
from uin_engine.domain.events import DialogueOccurred
from uin_engine.domain.value_objects import KnowledgeEntry
from uin_engine.application.services.memory_service import MemoryService


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
        memory_service: MemoryService,
    ):
        self._repo = world_repository
        self._bus = event_bus
        self._llm = llm_service
        self._memory_service = memory_service

    async def execute(self, command: TalkToCharacterCommand) -> tuple[DialogueGenerationResponse, GameWorld]:
        """
        Executes the dialogue logic.
        1. Fetches state and validates.
        2. Builds context for the LLM, including all possible facts for extraction.
        3. Calls the LLM service to get a response and potentially revealed facts.
        4. Updates semantic memory (`knowledge`) for the character who learned the facts.
        5. Updates episodic memory (`narrative_memory`) for both participants.
        6. Publishes an event with revealed fact IDs.
        7. Triggers memory compression if needed.
        8. Returns the response and the updated world.
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

        recent_history_str = "\n".join(listener.narrative_memory[-10:])
        all_facts_str = "\n".join([f"{fact.id}: {fact.content}" for fact in world.facts.values()])

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
            all_scenario_facts=all_facts_str,
        )

        response = await self._llm.generate_dialogue(context)
        time_str = world.game_time.strftime('%H:%M')

        # --- Update Episodic Memory (Narrative Log) ---
        speaker.narrative_memory.append(f"[{time_str}] I said to {listener.name}: \"{command.message}\"")
        listener.narrative_memory.append(f"[{time_str}] {speaker.name} said to me: \"{command.message}\"")
        listener.narrative_memory.append(f"[{time_str}] I replied to {speaker.name}: \"{response.text}\"")
        speaker.narrative_memory.append(f"[{time_str}] {listener.name} replied to me: \"{response.text}\"")

        # --- Update Semantic Memory (Knowledge) ---
        # The speaker (player) is the one listening to the response and learning the facts.
        if response.newly_revealed_facts:
            for fact_id in response.newly_revealed_facts:
                if fact_id not in speaker.knowledge:
                    speaker.knowledge[fact_id] = KnowledgeEntry(fact_id=fact_id, certainty=1.0)
                    fact_content = world.facts.get(fact_id).content if world.facts.get(fact_id) else "a new fact"
                    # Log the learning event *after* the dialogue that caused it.
                    speaker.narrative_memory.append(
                        f"[{time_str}] I learned something new from {listener.name}: {fact_content}"
                    )
                    print(f"[DEBUG] Player learned new fact: {fact_id}")

        # --- Deprecated: Update global dialogue history ---
        world.dialogue_history.append(DialogueEntry(
            speaker_id=speaker.id, listener_id=listener.id, message=command.message, game_time=world.game_time
        ))
        world.dialogue_history.append(DialogueEntry(
            speaker_id=listener.id, listener_id=speaker.id, message=response.text, game_time=world.game_time
        ))

        # --- Persist and Notify ---
        await self._repo.save(world)

        event = DialogueOccurred(
            speaker_id=speaker.id,
            listener_id=listener.id,
            dialogue_text=response.text,
            revealed_fact_ids=response.newly_revealed_facts
        )
        await self._bus.publish(event)
        
        # --- Trigger Memory Compression ---
        self._memory_service.compress_memory_if_needed(world, speaker)
        self._memory_service.compress_memory_if_needed(world, listener)

        return response, world

