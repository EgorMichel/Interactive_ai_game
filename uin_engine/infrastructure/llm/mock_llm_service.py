import re
from typing import List
from uin_engine.application.ports.llm_service import (
    ILLMService,
    DialogueGenerationContext,
    DialogueGenerationResponse,
)


class MockLLMService(ILLMService):
    """
    A mock implementation of the ILLMService for testing and development.
    It mimics the behavior of the real service, including parsing for fact tags.
    """
    def __init__(self):
        # This response can be overridden in tests for different scenarios
        self.canned_response_text = (
            "My name is {listener_name}. You, {speaker_name}, "
            "asked me about '{current_topic}'. This is a mock response. "
            "Sometimes I might reveal a fact, like that there is a [FACT_REVEALED: bloody_knife]."
        )

    async def generate_dialogue(self, context: DialogueGenerationContext) -> DialogueGenerationResponse:
        """
        Generates a predictable response and parses it for fact tags,
        just like the real LitellmService.
        """
        raw_text = self.canned_response_text.format(
            listener_name=context.listener_name,
            speaker_name=context.speaker_name,
            current_topic=context.current_topic
        )

        fact_tag_pattern = r'\[FACT_REVEALED:\s*(\w+)\s*\]'
        revealed_fact_ids = re.findall(fact_tag_pattern, raw_text)
        cleaned_text = re.sub(fact_tag_pattern, '', raw_text).strip()

        return DialogueGenerationResponse(
            text=cleaned_text,
            newly_revealed_facts=revealed_fact_ids,
            emotional_impact={}
        )

    async def batch_generate_dialogues(self, contexts: List[DialogueGenerationContext]) -> List[DialogueGenerationResponse]:
        """
        Simply calls the single-response generator for each context in the batch.
        """
        return [await self.generate_dialogue(ctx) for ctx in contexts]

    async def summarize(self, text_to_summarize: str) -> str:
        """
        Returns a hardcoded summary for testing purposes.
        """
        return f"This is a mock summary of the following text: {text_to_summarize[:30]}..."
