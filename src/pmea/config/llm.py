from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AI_PROVIDER_GOOGLE = "google"
AI_PROVIDER_OLLAMA = "ollama"

known_ai_providers = [AI_PROVIDER_GOOGLE, AI_PROVIDER_OLLAMA]

class LLMConfig(BaseSettings):
    """LLM provider configuration
    provider: one of 'ollama' or 'google' (required)
    """
    model_config = SettingsConfigDict(extra="ignore", env_prefix="")
    provider: str = Field(..., description="LLM provider, one of 'ollama' or 'google'", env="LLM_PROVIDER")
    api_key: str = Field(..., description="API key for the LLM service", env="LLM_API_KEY")
    model_name: str = Field(..., description="Model name to use", env="LLM_MODEL_NAME")
    temperature: float = Field(0.7, description="Temperature for generation", env="LLM_TEMPERATURE")

    @validator("provider")
    def validate_provider(cls, v: str):
        if v not in known_ai_providers:
            raise ValueError(f"provider must be one of {known_ai_providers}")
        return v