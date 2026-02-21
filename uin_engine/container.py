from dependency_injector import containers, providers

from uin_engine.application.use_cases.move_character import MoveCharacterHandler

from uin_engine.application.use_cases.talk_to_character import TalkToCharacterHandler

from uin_engine.application.use_cases.examine_object import ExamineObjectHandler

from uin_engine.application.use_cases.accuse_character import AccuseCharacterHandler

from uin_engine.application.use_cases.end_dialogue import EndDialogueHandler

from uin_engine.application.services.npc_behavior_system import NPCBehaviorSystem

from uin_engine.application.services.memory_service import MemoryService

from uin_engine.infrastructure.event_bus.local_event_bus import LocalEventBus

from uin_engine.infrastructure.llm.litellm_service import LitellmService

from uin_engine.infrastructure.llm.ollama_service import OllamaLLMService

from uin_engine.infrastructure.logging.file_logger import FileLogger

from uin_engine.infrastructure.logging.event_handler import LoggingEventHandler

from uin_engine.infrastructure.repositories.in_memory_world_repository import InMemoryWorldRepository

from uin_engine.infrastructure.config.scenario_loader import ScenarioLoader

from uin_engine.infrastructure.config import settings





class Container(containers.DeclarativeContainer):

    """

    The Dependency Injection (DI) container for the application.

    It wires together the different components of the system.

    """

    # =====================================================================

    # Infrastructure Layer

    # =====================================================================

    world_repository = providers.Singleton(InMemoryWorldRepository)

    event_bus = providers.Singleton(LocalEventBus)

    logger = providers.Singleton(FileLogger, log_file="game.log")

    scenario_loader = providers.Singleton(ScenarioLoader)

    # =====================================================================

    # LLM Service (Provider Selection)

    # =====================================================================

    # LiteLLM adapter (for OpenAI, Anthropic, Azure, etc.)
    litellm_service = providers.Singleton(

        LitellmService,

        event_bus=event_bus

    )

    # Ollama adapter (for local models)
    ollama_service = providers.Singleton(

        OllamaLLMService,

        event_bus=event_bus

    )

    # Factory that selects the appropriate LLM service based on settings
    # Access providers via Container class name
    llm_service = providers.Factory(

        lambda: Container.ollama_service() if settings.llm.provider == "ollama" else Container.litellm_service()

    )



    # =====================================================================

    # Application Layer (Services)

    # =====================================================================

    memory_service = providers.Singleton(

        MemoryService,

        llm_service=llm_service,

    )



    # =====================================================================

    # Application Layer (Use Case Handlers)

    # =====================================================================

    move_character_handler = providers.Factory(

        MoveCharacterHandler,

        event_bus=event_bus,

        memory_service=memory_service,

    )



    talk_to_character_handler = providers.Factory(

        TalkToCharacterHandler,

        event_bus=event_bus,

        llm_service=llm_service,

    )



    end_dialogue_handler = providers.Factory(

        EndDialogueHandler,

        memory_service=memory_service,

        event_bus=event_bus,

    )



    examine_object_handler = providers.Factory(

        ExamineObjectHandler,

        event_bus=event_bus,

        memory_service=memory_service,

    )



    accuse_character_handler = providers.Factory(

        AccuseCharacterHandler,

        world_repository=world_repository,

    )

    

    npc_behavior_system = providers.Singleton(

        NPCBehaviorSystem,

        move_character_handler=move_character_handler,

    )



    # =====================================================================

    # Logging

    # =====================================================================

    logging_event_handler = providers.Singleton(

        LoggingEventHandler,

        logger=logger,

        world_repository=world_repository,

    )



# A global instance of the container

container = Container()



def wire_dependencies():

    """

    Connects (wires) the components together.

    This function should be called once at application startup.

    """

    # Subscribe the logging handler to the event bus

    logging_handler = container.logging_event_handler()

    event_bus = container.event_bus()

    logging_handler.subscribe(event_bus)



    print("Dependencies wired and event handlers subscribed.")



async def initialize_llm():

    """

    Initialize the LLM service (pre-load model for Ollama).

    Call this after wire_dependencies() at application startup.

    """

    llm_service = container.llm_service()
    
    # Check if the service has an initialize method (OllamaLLMService does)
    if hasattr(llm_service, 'initialize'):
        await llm_service.initialize()
