from dependency_injector import containers, providers

from uin_engine.application.use_cases.move_character import MoveCharacterHandler
from uin_engine.application.use_cases.talk_to_character import TalkToCharacterHandler
from uin_engine.application.use_cases.examine_object import ExamineObjectHandler
from uin_engine.application.services.npc_behavior_system import NPCBehaviorSystem
from uin_engine.application.services.memory_service import MemoryService
from uin_engine.infrastructure.event_bus.local_event_bus import LocalEventBus
from uin_engine.infrastructure.llm.litellm_service import LitellmService



from uin_engine.infrastructure.repositories.in_memory_world_repository import InMemoryWorldRepository
from uin_engine.infrastructure.config.scenario_loader import ScenarioLoader


class Container(containers.DeclarativeContainer):
    """
    The Dependency Injection (DI) container for the application.
    It wires together the different components of the system.
    """
    # Configuration (if we had any, it would go here)
    # config = providers.Configuration()

    # =====================================================================
    # Infrastructure Layer
    # =====================================================================
    # A single instance of each infrastructure service is shared across the app
    # This is known as the Singleton scope.
    world_repository = providers.Singleton(InMemoryWorldRepository)
    event_bus = providers.Singleton(LocalEventBus)
    llm_service = providers.Singleton(LitellmService)
    scenario_loader = providers.Singleton(ScenarioLoader)

    # =====================================================================
    # Application Layer (Services)
    # =====================================================================
    memory_service = providers.Singleton(
        MemoryService,
        llm_service=llm_service,
        world_repository=world_repository,
    )

    # =====================================================================
    # Application Layer (Use Case Handlers)
    # =====================================================================
    # Handlers are created on-demand (Factory scope).
    # The container automatically injects the required dependencies.
    move_character_handler = providers.Factory(
        MoveCharacterHandler,
        world_repository=world_repository,
        event_bus=event_bus,
        memory_service=memory_service,
    )

    talk_to_character_handler = providers.Factory(
        TalkToCharacterHandler,
        world_repository=world_repository,
        event_bus=event_bus,
        llm_service=llm_service,
        memory_service=memory_service,
    )

    examine_object_handler = providers.Factory(
        ExamineObjectHandler,
        world_repository=world_repository,
        event_bus=event_bus,
        memory_service=memory_service,
    )
    
    npc_behavior_system = providers.Singleton(
        NPCBehaviorSystem,
        world_repository=world_repository,
        move_character_handler=move_character_handler,
    )

# A global instance of the container
container = Container()
