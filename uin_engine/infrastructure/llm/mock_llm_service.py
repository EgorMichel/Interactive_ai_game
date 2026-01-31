from typing import List
from uin_engine.application.ports.llm_service import (
    ILLMService,
    DialogueGenerationContext,
    DialogueGenerationResponse,
)


class MockLLMService(ILLMService):
    """
    A mock implementation of the ILLMService for testing and development.
    It bypasses any real AI model calls and returns a predictable,
    hardcoded response. This is crucial for fast, reliable, and cheap tests.
    """
    async def generate_dialogue(self, context: DialogueGenerationContext) -> DialogueGenerationResponse:
        """
        Generates a simple, canned response that incorporates some of the context
        to make testing more robust.
        """
        response_text = (
            f"My name is {context.listener_name}. You, {context.speaker_name}, "
            f"asked me about '{context.current_topic}'. This is a mock response."
        )

        return DialogueGenerationResponse(
            text=response_text,
            newly_revealed_facts=["a_fact_was_revealed_by_mock"],
            emotional_impact={"trust": -0.05, "curiosity": 0.1}
        )

    async def batch_generate_dialogues(self, contexts: List[DialogueGenerationContext]) -> List[DialogueGenerationResponse]:
        """
        Simply calls the single-response generator for each context in the batch.
        """
        # In a real batch implementation, this would be a single API call.
        return [await self.generate_dialogue(ctx) for ctx in contexts]
