import asyncio
import json
import re
import subprocess
from typing import List, Optional

from uin_engine.application.ports.llm_service import (
    ILLMService,
    DialogueGenerationContext,
    DialogueGenerationResponse,
)
from uin_engine.application.ports.event_bus import IEventBus
from uin_engine.domain.events import LLMRequestSent
from uin_engine.infrastructure.config import settings


class OllamaLLMService(ILLMService):
    """
    Implementation of ILLMService using Ollama REST API via subprocess + curl.
    This approach works around issues with Python HTTP clients on Windows with Python 3.13.
    
    It connects to a local Ollama instance (http://localhost:11434)
    and provides access to locally running models (e.g., gemma3:1b, llama2, etc.).

    This adapter follows the same interface as LitellmService to ensure
    interchangeability through dependency injection.
    """

    DEFAULT_BASE_URL = "http://localhost:11434"
    DEFAULT_TIMEOUT = 120  # Local models can be slower, especially on first load

    def __init__(self, event_bus: IEventBus):
        self._bus = event_bus
        self._base_url = settings.llm.api_base or self.DEFAULT_BASE_URL
        self._model_name = settings.llm.model_name
        self._timeout = settings.llm.timeout or self.DEFAULT_TIMEOUT
        self._initialized = False

        # Ensure model name doesn't have 'ollama/' prefix for direct API calls
        if self._model_name.startswith("ollama/"):
            self._model_name = self._model_name[7:]

        print(f"[OllamaLLMService] Using model: {self._model_name}, Base URL: {self._base_url}")
        print(f"[OllamaLLMService] Using subprocess + curl for API calls.")

    async def initialize(self):
        """
        Pre-load the model into Ollama memory.
        This sends a minimal request to ensure the model is loaded before gameplay starts.
        """
        if self._initialized:
            return

        print(f"[OllamaLLMService] Loading model '{self._model_name}' into memory...")
        print("[OllamaLLMService] This may take 10-60 seconds depending on your hardware.")

        try:
            # Send a minimal request to trigger model loading
            preload_messages = [
                {"role": "user", "content": "Respond with just 'OK'."}
            ]

            payload = {
                "model": self._model_name,
                "messages": preload_messages,
                "stream": False,
                "options": {"temperature": 0, "num_predict": 5}
            }

            result = await asyncio.get_event_loop().run_in_executor(
                None, self._call_ollama_api, "/api/chat", payload
            )

            if result.get('success'):
                print(f"[OllamaLLMService] Model '{self._model_name}' loaded successfully!")
                self._initialized = True
            else:
                error = result.get('error', 'Unknown error')
                print(f"[OllamaLLMService] WARNING: Model loading failed: {error}")
                print("[OllamaLLMService] The model will be loaded on first request instead.")

        except Exception as e:
            print(f"[OllamaLLMService] WARNING: Failed to preload model: {e}")
            print("[OllamaLLMService] The model will be loaded on first request instead.")

    def _call_ollama_api(self, endpoint: str, payload: dict) -> dict:
        """
        Call Ollama API using subprocess + curl.
        Returns dict with 'success': True/False and 'data' or 'error'.
        """
        url = f"{self._base_url}{endpoint}"
        try:
            result = subprocess.run(
                ["curl", "-s", "-X", "POST", url,
                 "-H", "Content-Type: application/json",
                 "-d", json.dumps(payload)],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=self._timeout
            )

            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                return {"success": True, "data": data}
            elif result.returncode == 0:
                return {"success": False, "error": "Empty response from Ollama"}
            else:
                return {"success": False, "error": f"curl error: {result.stderr}"}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Request timed out after {self._timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _build_messages_from_context(self, context: DialogueGenerationContext) -> List[dict]:
        """
        Transforms our DialogueGenerationContext into the message format expected by Ollama.
        Same logic as in LitellmService for consistency.
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
    
    async def _get_llm_response(self, messages: List[dict]) -> str:
        """
        Makes an async request to Ollama using subprocess + curl.
        Implements retry logic for transient errors.
        """
        max_retries = 3
        options = {
            "temperature": 0.7,
            "num_predict": 200,  # Similar to max_tokens in OpenAI
        }

        payload = {
            "model": self._model_name,
            "messages": messages,
            "stream": False,
            "options": options,
        }

        for attempt in range(max_retries):
            try:
                # Run blocking subprocess call in executor to not block event loop
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self._call_ollama_api, "/api/chat", payload
                )

                if result.get('success'):
                    data = result['data']
                    return data.get('message', {}).get('content', '').strip()
                else:
                    error = result.get('error', 'Unknown error')
                    print(f"Attempt {attempt + 1}/{max_retries}: Ollama request failed. Error: {error}")

                    # Check for specific error types
                    if "curl error" in error.lower() or "connect" in error.lower():
                        if attempt + 1 == max_retries:
                            raise ConnectionError(
                                f"Cannot connect to Ollama at {self._base_url}. "
                                "Ensure Ollama is running (run 'ollama serve' or start Ollama app)."
                            )
                    elif "timed out" in error.lower():
                        if attempt + 1 == max_retries:
                            raise TimeoutError(
                                f"Ollama request timed out after {self._timeout}s. "
                                "Try increasing LLM_TIMEOUT or using a smaller model."
                            )
                    elif "not found" in error.lower() or "404" in error:
                        raise ValueError(
                            f"Model '{self._model_name}' not found. "
                            f"Run 'ollama pull {self._model_name}' to download it."
                        )

                    if attempt + 1 == max_retries:
                        raise Exception(f"Ollama request failed after {max_retries} attempts: {error}")

                    await asyncio.sleep(1)

            except (ConnectionError, TimeoutError, ValueError):
                raise
            except Exception as e:
                print(f"Attempt {attempt + 1}/{max_retries}: Unexpected error: {e}")
                if attempt + 1 == max_retries:
                    raise
                await asyncio.sleep(1)

        return "I'm sorry, I could not process your request due to a persistent error."

    async def generate_dialogue(self, context: DialogueGenerationContext) -> DialogueGenerationResponse:
        """
        Generates a single dialogue response using Ollama, publishing a debug event
        beforehand and parsing the response for revealed facts.
        """
        messages = self._build_messages_from_context(context)

        # Publish a debug event with the full prompt and memory
        debug_event = LLMRequestSent(
            listener_id=context.listener_name,
            full_prompt=messages[0]["content"],
            raw_memory=context.recent_dialogue_history
        )
        await self._bus.publish(debug_event)

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
        """
        Generates multiple dialogue responses in parallel using asyncio.gather.
        """
        tasks = [self.generate_dialogue(ctx) for ctx in contexts]
        return await asyncio.gather(*tasks)

    async def summarize(self, text_to_summarize: str) -> str:
        """
        Summarizes a given block of text using Ollama.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant. Your task is to summarize the following text concisely, "
                    "capturing the main events, topics of conversation, and key insights from the perspective of the person "
                    "whose memory this is. Start the summary with 'My memory of this time is that...'"
                )
            },
            {
                "role": "user",
                "content": text_to_summarize
            }
        ]
        summary = await self._get_llm_response(messages)
        return summary
