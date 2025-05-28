"""LLM provider configuration."""
import os
from typing import Callable, Self
from pydantic import Field, model_validator, validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

AI_PROVIDER_GOOGLE = "google"
AI_PROVIDER_OLLAMA = "ollama"
_DEFAULT_OLLAMA_URL = "http://localhost:11434"

known_ai_providers = [AI_PROVIDER_GOOGLE, AI_PROVIDER_OLLAMA]

class OllamaOptions(BaseSettings):
    base_url: str = Field(default=_DEFAULT_OLLAMA_URL, description="Ollama server base URL")
    context_length: int = Field(default=8192, description="Context length for Ollama")
    no_think: bool = Field(default=False, description="Disable model reasoning")

class LLMConfig(BaseSettings):
    """LLM provider configuration
    provider: one of 'ollama' or 'google' (required)
    """
    model_config = SettingsConfigDict(extra="ignore", env_prefix="")
    provider: str = Field(..., description="LLM provider, one of 'ollama' or 'google'")
    api_key: str = Field(default='', description="API key for the LLM service")
    model_name: str = Field(..., description="Model name to use")
    temperature: float = Field(default=0.7, description="Temperature for generation")
    ollama_options: OllamaOptions = Field(default_factory=OllamaOptions, description="Ollama-specific options")
    model_options: dict = Field(default_factory=dict, description="Additional model options")

    @validator("provider")
    def validate_provider(cls, v: str):
        if v not in known_ai_providers:
            raise ValueError(f"provider must be one of {known_ai_providers}")
        return v

    @model_validator(mode='after')
    def _resolve_and_validate_api_key(self) -> Self:
        """Ensures API key is present for cloud providers, loading from env if necessary."""
        if self.provider == AI_PROVIDER_OLLAMA:
            return self

        if self.provider == AI_PROVIDER_GOOGLE:
            if not self.api_key:
                self.api_key = os.getenv("GEMINI_API_KEY", "")
            if not self.api_key:
                raise ValueError(
                    "API key is required for Google provider. "
                    "Provide it directly or set the GEMINI_API_KEY environment variable."
                )
        return self

    def get_system_prompt_extra(self) -> str | None:
        if self.provider == AI_PROVIDER_OLLAMA and self.ollama_options.no_think:
            return "/no_think"
        return None

    def get_model_provider(self) -> Callable[[], BaseChatModel]:
        if self.provider == AI_PROVIDER_GOOGLE:
            return lambda: ChatGoogleGenerativeAI(
                google_api_key=self.api_key,
                model=self.model_name,
                temperature=self.temperature,
                **self.model_options,
            )
        elif self.provider == AI_PROVIDER_OLLAMA:
            return lambda: ChatOllama(
                base_url=self.ollama_options.base_url,
                model=self.model_name,
                temperature=self.temperature,
                num_ctx=self.ollama_options.context_length,
                extract_reasoning=True,
                **self.model_options,
            )
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")