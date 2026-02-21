from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Literal


class LLMSettings(BaseSettings):
    """
    Settings for Large Language Models.
    Loads from environment variables (prefixed with LLM_).
    """
    model_config = SettingsConfigDict(env_prefix='LLM_', env_file='.env', extra='ignore')

    # Provider selection: 'litellm' for OpenAI/Anthropic/etc via LiteLLM, 'ollama' for local models
    provider: Literal["litellm", "ollama"] = "litellm"
    
    api_key: str = "" # LiteLLM can pick this up from OS environment, but good to have explicit
    api_base: Optional[str] = None # Base URL for LLM API (e.g., for local models or custom endpoints)

    # This is a safe default. It's STRONGLY recommended to set a specific,
    # provider-supported model in your .env file, as this default may not
    # be compatible with all third-party API endpoints.
    model_name: str = "openai/gpt-4o" # Default model to use

    # Timeout for LLM requests (in seconds). Useful for local models which can be slower.
    timeout: Optional[float] = None

    # LiteLLM specific settings
    # For example, if using Azure:
    # azure_api_key: Optional[str] = None
    # azure_api_base: Optional[str] = None
    # azure_api_version: Optional[str] = None


class Settings(BaseSettings):
    """
    Main application settings.
    """
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    llm: LLMSettings = LLMSettings()

# Export a single instance of settings for easy access throughout the app.
settings = Settings()
