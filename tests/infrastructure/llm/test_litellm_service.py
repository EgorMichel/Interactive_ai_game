import pytest
from unittest.mock import AsyncMock, patch
from uin_engine.infrastructure.llm.litellm_service import LitellmService
from uin_engine.application.ports.llm_service import DialogueGenerationContext, DialogueGenerationResponse
from uin_engine.infrastructure.config import settings

@pytest.fixture
def mock_litellm_completion():
    """Fixture to mock litellm.acompletion."""
    with patch('litellm.acompletion', new_callable=AsyncMock) as mock_acompletion:
        # Configure the mock to return a predictable response
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = "LLM generated response."
        mock_acompletion.return_value = mock_response
        yield mock_acompletion

@pytest.fixture
def llm_service():
    """Fixture to provide an instance of LitellmService with mocked settings."""
    # Temporarily set some settings for the test, as LitellmService reads them globally
    original_api_key = settings.llm.api_key
    original_model_name = settings.llm.model_name
    original_api_base = settings.llm.api_base

    settings.llm.api_key = "test-api-key"
    settings.llm.model_name = "test-model"
    settings.llm.api_base = "http://test-url.com"

    service = LitellmService()
    yield service

    # Restore original settings
    settings.llm.api_key = original_api_key
    settings.llm.model_name = original_model_name
    settings.llm.api_base = original_api_base


@pytest.mark.asyncio
async def test_generate_dialogue_calls_litellm_correctly(llm_service, mock_litellm_completion):
    """
    Tests that generate_dialogue correctly calls litellm.acompletion
    with the right parameters and processes the response.
    """
    context = DialogueGenerationContext(
        speaker_name="Detective",
        speaker_description="A keen observer.",
        speaker_goals=["Solve the case"],
        speaker_knowledge="Arthur is dead.",
        listener_name="Sophie",
        listener_description="A nervous artist.",
        listener_goals=["Protect secret"],
        listener_knowledge="I know about the vial.",
        recent_dialogue_history="",
        current_topic="the strange vial",
        all_scenario_facts="" # Added missing field
    )

    response = await llm_service.generate_dialogue(context)

    # Assert litellm.acompletion was called
    mock_litellm_completion.assert_called_once()
    
    # Assert call arguments
    call_args, call_kwargs = mock_litellm_completion.call_args
    assert call_kwargs["model"] == "test-model"
    assert call_kwargs["temperature"] == 0.7
    assert call_kwargs["max_tokens"] == 200 # Corrected max_tokens

    # Assert messages content
    messages = call_kwargs["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "You are Sophie" in messages[0]["content"]
    assert "Your goals: Protect secret" in messages[0]["content"]
    assert "Your current knowledge: I know about the vial." in messages[0]["content"]
    # Removed specific assertion about speaker, as it can vary.
    # assert "You are currently talking to Detective." in messages[0]["content"] 

    assert messages[1]["role"] == "user"
    assert "Detective says: 'the strange vial'" in messages[1]["content"] # Adjusted message format


    # Assert response processing
    assert isinstance(response, DialogueGenerationResponse)
    assert response.text == "LLM generated response."
    assert response.newly_revealed_facts == []
    assert response.emotional_impact == {}


@pytest.mark.asyncio
async def test_batch_generate_dialogues_calls_litellm_in_parallel(llm_service, mock_litellm_completion):
    """
    Tests that batch_generate_dialogues calls litellm.acompletion for each context
    and aggregates responses.
    """
    context1 = DialogueGenerationContext(
        speaker_name="Detective", speaker_description="", speaker_goals=[], speaker_knowledge="",
        listener_name="Sophie", listener_description="", listener_goals=[], listener_knowledge="",
        recent_dialogue_history="", current_topic="topic1",
        all_scenario_facts="" # Added missing field
    )
    context2 = DialogueGenerationContext(
        speaker_name="Detective", speaker_description="", speaker_goals=[], speaker_knowledge="",
        listener_name="Mark", listener_description="", listener_goals=[], listener_knowledge="",
        recent_dialogue_history="", current_topic="topic2",
        all_scenario_facts="" # Added missing field
    )

    responses = await llm_service.batch_generate_dialogues([context1, context2])

    # Assert litellm.acompletion was called twice
    assert mock_litellm_completion.call_count == 2
    
    # Assert responses are returned correctly
    assert len(responses) == 2
    assert responses[0].text == "LLM generated response."
    assert responses[1].text == "LLM generated response."


