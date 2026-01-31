from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class LLMSettings(BaseSettings):
    """
    Settings for Large Language Models.
    Loads from environment variables (prefixed with LLM_).
    """
    model_config = SettingsConfigDict(env_prefix='LLM_', env_file='.env', extra='ignore')

    api_key: str = "" # LiteLLM can pick this up from OS environment, but good to have explicit
    api_base: Optional[str] = None # Base URL for LLM API (e.g., for local models or custom endpoints)
    model_name: str = "gpt-3.5-turbo" # Default model to use

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
