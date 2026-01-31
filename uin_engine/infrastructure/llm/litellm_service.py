import asyncio
import os
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
        
        # Automatically drop any parameters that the model does not support
        litellm.drop_params = True

        # This is a temporary setup. In a more complex app, you might pass
        # specific configs per LLM model, or set up routing.
        self.model_name = settings.llm.model_name
        self._set_env_variables_for_litellm()

        print(f"[LLM] Using LiteLLM with model: {self.model_name}, API Base: {litellm.api_base or 'default'}")

    def _set_env_variables_for_litellm(self):
        """
        LiteLLM can pick up keys from env vars.
        Ensure our settings are reflected in the environment if not directly used.
        """
        if settings.llm.api_key:
            # LiteLLM uses OPENAI_API_KEY for many OpenAI-compatible models
            os.environ["OPENAI_API_KEY"] = settings.llm.api_key
        if settings.llm.api_base:
            os.environ["OPENAI_API_BASE"] = settings.llm.api_base
        # Add more specific env vars if we plan to use specific providers beyond OpenAI-compatible
        # e.g., os.environ["ANTHROPIC_API_KEY"] = ...


    async def _get_llm_response(self, messages: List[dict]) -> str:
        """
        Helper to make a single litellm call with a retry mechanism for transient errors.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await litellm.acompletion(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.7, # A bit creative, but not wild
                    max_tokens=150,  # Limit response length for dialogue
                )
                # LiteLLM's response structure is similar to OpenAI's
                return response.choices[0].message.content.strip()
            except (litellm.APIConnectionError, litellm.Timeout, litellm.ServiceUnavailableError) as e:
                print(f"LLM call failed on attempt {attempt + 1}/{max_retries}. Retrying... Error: {e}")
                if attempt + 1 == max_retries:
                    # Last attempt failed, re-raise the exception
                    raise e
                await asyncio.sleep(1) # Wait 1 second before retrying
            except Exception as e:
                # For non-retriable errors (like BadRequestError), fail immediately
                print(f"Error calling LiteLLM: {e}")
                # We re-raise the exception to be caught by the CLI loop
                raise e
        
        # This line should not be reached if retries fail, but as a fallback:
        return "I'm sorry, I could not process your request due to a persistent error."

    def _build_messages_from_context(self, context: DialogueGenerationContext) -> List[dict]:
        """
        Transforms our DialogueGenerationContext into the message format expected by LLMs.
        """
        # System message defines the role of the NPC
        system_message = (
            f"You are {context.listener_name}, a character in a mystery game on a yacht. "
            f"Your description: {context.listener_description}. "
            f"Your goals: {', '.join(context.listener_goals)}. "
            f"Your current knowledge: {context.listener_knowledge}. "
            "Respond naturally, stay in character, and keep your answers concise. "
            "Do not reveal information you don't know or that would break character. "
            f"You are currently talking to {context.speaker_name}."
        )
        
        # Add recent dialogue history to give context to the conversation
        if context.recent_dialogue_history:
            system_message += (
                f"\n\nHere is the recent conversation history between you and {context.speaker_name}:\n"
                f"{context.recent_dialogue_history}"
            )

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"{context.speaker_name} says: '{context.current_topic}'"}
        ]
        return messages


    async def generate_dialogue(self, context: DialogueGenerationContext) -> DialogueGenerationResponse:
        """
        Generates a single dialogue response using LiteLLM.
        """
        messages = self._build_messages_from_context(context)
        llm_content = await self._get_llm_response(messages)

        return DialogueGenerationResponse(
            text=llm_content,
            newly_revealed_facts=[],  # LiteLLM is not currently set up to extract structured facts
            emotional_impact={}       # Similar to above, this would need specific prompt engineering
        )

    async def batch_generate_dialogues(self, contexts: List[DialogueGenerationContext]) -> List[DialogueGenerationResponse]:
        """
        Generates multiple dialogue responses in a single batch call for efficiency.
        Note: LiteLLM's acompletion does not natively batch *different* conversations
        into one API call to the backend LLM. This will essentially run them in parallel.
        """
        tasks = [self.generate_dialogue(ctx) for ctx in contexts]
        return await asyncio.gather(*tasks)
