import uuid
from uin_engine.application.ports.event_bus import IEventBus
from uin_engine.application.ports.llm_service import ILLMService, DialogueGenerationContext, DialogueGenerationResponse
from uin_engine.application.commands.dialogue import TalkToCharacterCommand
from uin_engine.domain.events import DialogueOccurred
from uin_engine.domain.value_objects import KnowledgeEntry
from uin_engine.domain.entities import GameWorld, DialogueSession, DialogueReplica, DialogueSessionId

class TalkToCharacterHandler:
    """
    Handles the TalkToCharacterCommand use case.
    Manages dialogue sessions, from creation to continuation.
    """
    def __init__(self, event_bus: IEventBus, llm_service: ILLMService):
        self._bus = event_bus
        self._llm = llm_service

    async def execute(self, command: TalkToCharacterCommand, world: GameWorld) -> tuple[GameWorld, DialogueSessionId]:
        """
        Executes the dialogue logic.
        - If no session_id is provided, creates a new DialogueSession.
        - If a message is provided, adds it to the session and gets an LLM response.
        - Returns the updated world and the session ID.
        """
        speaker = world.characters.get(command.speaker_id)
        listener = world.characters.get(command.listener_id)

        if not speaker or not listener:
            raise ValueError("Invalid speaker or listener.")
        if speaker.location_id != listener.location_id:
            raise ValueError(f"{speaker.name} and {listener.name} are not in the same location.")

        # Find or create a dialogue session
        if command.session_id and command.session_id in world.active_dialogues:
            session = world.active_dialogues[command.session_id]
        else:
            session_id = DialogueSessionId(str(uuid.uuid4()))
            session = DialogueSession(id=session_id, participants=[speaker.id, listener.id])
            world.active_dialogues[session_id] = session
        
        # If there's no message, we are just initiating the dialogue.
        if not command.message:
            return world, session.id

        # Add player's message to the session history
        session.history.append(DialogueReplica(speaker_id=speaker.id, message=command.message, game_time=world.game_time))

        # Build context for LLM
        long_term_mem = listener.narrative_memory[-5:] # Get last 5 long-term memories
        current_dialogue = [f"{world.characters[r.speaker_id].name}: \"{r.message}\"" for r in session.history]
        
        # Combine long-term and short-term memory for the prompt
        history_for_prompt = "\n".join(long_term_mem + current_dialogue)

        context = DialogueGenerationContext(
            speaker_name=speaker.name,
            speaker_description=speaker.description,
            speaker_goals=speaker.goals,
            speaker_knowledge="; ".join([world.facts[f_id].content for f_id in speaker.knowledge]),
            listener_name=listener.name,
            listener_description=listener.description,
            listener_goals=listener.goals,
            listener_knowledge="; ".join([world.facts[f_id].content for f_id in listener.knowledge]),
            recent_dialogue_history=history_for_prompt,
            current_topic=command.message,
            all_scenario_facts="\n".join([f"{f.id}: {f.content}" for f in world.facts.values()]),
        )

        response = await self._llm.generate_dialogue(context)

        # Add listener's response to session history
        session.history.append(DialogueReplica(speaker_id=listener.id, message=response.text, game_time=world.game_time))
        
        # Update speaker's semantic memory if new facts were revealed
        if response.newly_revealed_facts:
            for fact_id in response.newly_revealed_facts:
                if fact_id in world.facts and fact_id not in speaker.knowledge:
                    speaker.knowledge[fact_id] = KnowledgeEntry(fact_id=fact_id, certainty=1.0)
                    print(f"[DEBUG] Player learned new fact: {fact_id}")

        # Publish event for logging
        event = DialogueOccurred(
            speaker_id=speaker.id,
            listener_id=listener.id,
            dialogue_text=response.text,
            revealed_fact_ids=response.newly_revealed_facts
        )
        await self._bus.publish(event, world)

        return world, session.id

