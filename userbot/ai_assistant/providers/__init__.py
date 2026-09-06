# AI Provider Layer - Abstract interface for AI services
from .base import AIProvider, openai_message_text
from .mistral import MistralProvider
from .nvidia import NVIDIAProvider
from .groq import GroqProvider
from .openrouter import OpenRouterProvider

# Provider registry
PROVIDERS = {
    "mistral": MistralProvider,
    "nvidia": NVIDIAProvider,
    "groq": GroqProvider,
    "openrouter": OpenRouterProvider,
}


def get_ai_provider(
    provider_name: str = "mistral", api_key: str = None, model: str = None
) -> AIProvider:
    """
    Factory function to get AI provider instance.

    Args:
        provider_name: Name of the provider (mistral|nvidia|groq|openrouter)
        api_key: API key for the provider
        model: Optional model name override

    Returns:
        AIProvider instance
    """
    key = provider_name.lower()
    provider_class = PROVIDERS.get(key)
    if not provider_class:
        raise ValueError(
            f"Unknown provider: {provider_name}. Available: {list(PROVIDERS.keys())}"
        )

    return provider_class(api_key=api_key, model=model)


__all__ = [
    "AIProvider",
    "openai_message_text",
    "get_ai_provider",
    "MistralProvider",
    "NVIDIAProvider",
    "GroqProvider",
    "OpenRouterProvider",
]
