import asyncio
import os
import re
from typing import List, Optional
import litellm

from uin_engine.application.ports.llm_service import (
    ILLMService,
    DialogueGenerationContext,
    DialogueGenerationResponse,
)
from uin_engine.infrastructure.config import settings


class LitellmService(ILLMService):
    """
    Implementation of ILLMService using the LiteLLM library.
    It connects to various LLM providers (OpenAI, Anthropic, local models via Ollama, etc.)
    through a unified API.
    """
    def __init__(self):
        # Configure LiteLLM globally from our settings
        litellm.api_key = settings.llm.api_key
        if settings.llm.api_base:
            litellm.api_base = settings.llm.api_base
        
        litellm.drop_params = True
        self.model_name = settings.llm.model_name
        self._set_env_variables_for_litellm()

        print(f"[LLM] Using LiteLLM with model: {self.model_name}, API Base: {litellm.api_base or 'default'}")

    def _set_env_variables_for_litellm(self):
        if settings.llm.api_key:
            os.environ["OPENAI_API_KEY"] = settings.llm.api_key
        if settings.llm.api_base:
            os.environ["OPENAI_API_BASE"] = settings.llm.api_base

    async def _get_llm_response(self, messages: List[dict]) -> str:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await litellm.acompletion(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=200, # Increased slightly to accommodate tags
                )
                return response.choices[0].message.content.strip()
            except (litellm.APIConnectionError, litellm.Timeout, litellm.ServiceUnavailableError) as e:
                print(f"LLM call failed on attempt {attempt + 1}/{max_retries}. Retrying... Error: {e}")
                if attempt + 1 == max_retries:
                    raise e
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Error calling LiteLLM: {e}")
                raise e
        return "I'm sorry, I could not process your request due to a persistent error."

    def _build_messages_from_context(self, context: DialogueGenerationContext) -> List[dict]:
        """
        Transforms our DialogueGenerationContext into the message format expected by LLMs,
        including instructions for fact extraction.
        """
        system_message_parts = [
            f"You are {context.listener_name}, a character in a mystery game. ",
            f"Your description: {context.listener_description}. ",
            f"Your goals: {', '.join(context.listener_goals)}. ",
            f"Your current knowledge: {context.listener_knowledge}. ",
            "Respond naturally, stay in character, and keep your answers concise. ",
            f"You are talking to {context.speaker_name}."
        ]

        # Only add fact-revelation instructions if there are facts to reveal
        if context.all_scenario_facts and context.all_scenario_facts.strip():
            system_message_parts.append(
                "\n\nIMPORTANT: If your response, or the user's message to you, directly reveals or confirms a crucial piece of information, "
                "you MUST append a special tag `[FACT_REVEALED: <fact_id>]` on a new line at the very end of your response. "
                "Do not add any text after the tag. You can add multiple tags if multiple facts are revealed.\n"
                "Example: If you say 'I saw a bloody knife...', you must append `[FACT_REVEALED: bloody_knife]`.\n\n"
                "Here is the list of possible facts you can reveal:\n"
                f"{context.all_scenario_facts}"
            )
        
        system_message = "".join(system_message_parts)

        if context.recent_dialogue_history:
            system_message += (
                f"\n\nHere is the recent conversation history:\n"
                f"{context.recent_dialogue_history}"
            )

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"{context.speaker_name} says: '{context.current_topic}'"}
        ]
        return messages

    async def generate_dialogue(self, context: DialogueGenerationContext) -> DialogueGenerationResponse:
        """
        Generates a single dialogue response using LiteLLM and parses it
        for revealed facts.
        """
        messages = self._build_messages_from_context(context)
        llm_raw_content = await self._get_llm_response(messages)

        # Regex to find all fact tags
        fact_tag_pattern = r'\[FACT_REVEALED:\s*(\w+)\s*\]'
        revealed_fact_ids = re.findall(fact_tag_pattern, llm_raw_content)

        # Clean the tags from the response text that will be shown to the user
        cleaned_text = re.sub(fact_tag_pattern, '', llm_raw_content).strip()

        return DialogueGenerationResponse(
            text=cleaned_text,
            newly_revealed_facts=revealed_fact_ids,
            emotional_impact={}
        )

    async def batch_generate_dialogues(self, contexts: List[DialogueGenerationContext]) -> List[DialogueGenerationResponse]:
        tasks = [self.generate_dialogue(ctx) for ctx in contexts]
        return await asyncio.gather(*tasks)

    async def summarize(self, text_to_summarize: str) -> str:
        """
        Summarizes a given block of text using the LLM.
        """
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant. Your task is to summarize the following text concisely, "
                           "capturing the main events, topics of conversation, and key insights from the perspective of the person "
                           "whose memory this is. Start the summary with 'My memory of this time is that...'"
            },
            {
                "role": "user",
                "content": text_to_summarize
            }
        ]
        summary = await self._get_llm_response(messages)
        return summary
