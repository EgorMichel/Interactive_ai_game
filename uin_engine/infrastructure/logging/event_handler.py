from typing import TypeVar, Optional
from uin_engine.application.ports.event_bus import IEventBus
from uin_engine.application.ports.logger import ILogger
from uin_engine.application.ports.world_repository import IWorldRepository
from uin_engine.domain.events import DomainEvent, CharacterMoved, FactDiscovered, DialogueOccurred, LLMRequestSent
from uin_engine.domain.entities import GameWorld

T = TypeVar('T')

class LoggingEventHandler:
    """
    An event handler that logs various domain events to a logger.
    """
    def __init__(self, logger: ILogger, world_repository: IWorldRepository):
        self._logger = logger
        self._world_repo = world_repository

    async def handle(self, event: DomainEvent, world: Optional[GameWorld] = None):
        """
        Generic handler that dispatches to specific methods based on event type.
        If the world state is not passed with the event, it fetches it from the repository.
        """
        try:
            # If the world context isn't provided with the event, fetch it.
            # This is necessary for events published from deep within the infrastructure layer.
            if not world:
                # TODO: Make world_id dynamic if multiple worlds are ever supported.
                world = await self._world_repo.get_by_id("yacht_mystery")
                if not world:
                    self._logger.error("LoggingEventHandler failed: Could not retrieve world for context.")
                    return

            # A simple router based on event type
            if isinstance(event, CharacterMoved):
                self._handle_character_moved(event, world)
            elif isinstance(event, DialogueOccurred):
                self._handle_dialogue_occurred(event, world)
            elif isinstance(event, FactDiscovered):
                self._handle_fact_discovered(event, world)
            elif isinstance(event, LLMRequestSent):
                self._handle_llm_request_sent(event, world)
            else:
                self._logger.debug(f"Received unknown event type: {type(event).__name__}")
        except Exception as e:
            self._logger.error(f"Error in LoggingEventHandler: {e}")

    def _handle_character_moved(self, event: CharacterMoved, world: GameWorld):
        char_name = world.characters.get(event.character_id, "Unknown").name
        from_loc_name = world.locations.get(event.from_location_id, "Unknown").name
        to_loc_name = world.locations.get(event.to_location_id, "Unknown").name
        game_time = world.game_time.strftime('%H:%M')
        self._logger.info(f"[{game_time}] CHARACTER MOVED: '{char_name}' moved from '{from_loc_name}' to '{to_loc_name}'.")

    def _handle_dialogue_occurred(self, event: DialogueOccurred, world: GameWorld):
        speaker_name = world.characters.get(event.speaker_id, "Unknown").name
        listener_name = world.characters.get(event.listener_id, "Unknown").name
        game_time = world.game_time.strftime('%H:%M')
        self._logger.info(f"[{game_time}] DIALOGUE: '{speaker_name}' said something to '{listener_name}'. Response: \"{event.dialogue_text}\"")
        if event.revealed_fact_ids:
            self._logger.info(f"[{game_time}] DIALOGUE REVEALED FACTS: {event.revealed_fact_ids}")

    def _handle_fact_discovered(self, event: FactDiscovered, world: GameWorld):
        char_name = world.characters.get(event.character_id, "Unknown").name
        fact_content = world.facts.get(event.fact_id, "Unknown").content
        game_time = world.game_time.strftime('%H:%M')
        self._logger.info(f"[{game_time}] FACT DISCOVERED: '{char_name}' discovered fact '{event.fact_id}' ('{fact_content}') by '{event.source}'.")

    def _handle_llm_request_sent(self, event: LLMRequestSent, world: GameWorld):
        game_time = world.game_time.strftime('%H:%M')
        log_message = (
            f"[{game_time}] LLM DEBUG: Preparing request for listener '{event.listener_id}'.\n"
            f"--- COMBINED MEMORY (from recent dialogue history) ---\n{event.raw_memory}\n"
            f"--- FULL PROMPT ---\n{event.full_prompt}\n"
            f"--- END PROMPT ---"
        )
        self._logger.debug(log_message)

    def subscribe(self, event_bus: IEventBus):
        """Subscribes the handler to all relevant events on the event bus."""
        event_bus.subscribe(DomainEvent, self.handle)
