"""LLM provider configuration."""
import os
from typing import Callable, Self
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

AI_PROVIDER_GOOGLE = "google"
AI_PROVIDER_OLLAMA = "ollama"
_DEFAULT_OLLAMA_URL = "http://localhost:11434"

known_ai_providers = [AI_PROVIDER_GOOGLE, AI_PROVIDER_OLLAMA]

class LLMConfig(BaseSettings):
    """LLM provider configuration
    provider: one of 'ollama' or 'google' (required)
    """
    model_config = SettingsConfigDict(extra="ignore", env_prefix="")
    base_url: str = Field(default='', description="Base URL for the LLM service")
    provider: str = Field(..., description="LLM provider, one of 'ollama' or 'google'")
    api_key: str = Field(default='', description="API key for the LLM service")
    model_name: str = Field(..., description="Model name to use")
    temperature: float = Field(default=0.7, description="Temperature for generation")
    model_kwarg: dict | None = Field(None, description="Additional keyword arguments to pass to the model")

    @validator("provider")
    def validate_provider(cls, v: str):
        if v not in known_ai_providers:
            raise ValueError(f"provider must be one of {known_ai_providers}")
        return v
    
    def with_defaults(self) -> Self:
        if self.provider == AI_PROVIDER_OLLAMA:
            return self

        if self.provider == AI_PROVIDER_GOOGLE and not self.api_key:
            self.api_key = os.getenv("GOOGLE_API_KEY", "")
        if not self.api_key:
            raise ValueError(f"API key is required for provider {self.provider}")
        return self

    def get_model_provider(self) -> Callable[[], BaseChatModel]:
        if self.provider == AI_PROVIDER_GOOGLE:
            return lambda: ChatGoogleGenerativeAI(
                google_api_key=self.api_key,
                model=self.model_name,
                temperature=self.temperature,
                model_kwargs=self.model_kwarg,
            )
        elif self.provider == AI_PROVIDER_OLLAMA:
            return lambda: ChatOllama(
                base_url=self.base_url or _DEFAULT_OLLAMA_URL,
                model=self.model_name,
                temperature=self.temperature,
            )
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")