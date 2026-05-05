# AI Provider Layer - Abstract interface for AI services
from .base import AIProvider
from .mistral import MistralProvider
from .nvidia import NVIDIAProvider

# Provider registry
PROVIDERS = {
    "mistral": MistralProvider,
    "nvidia": NVIDIAProvider,
}


def get_ai_provider(provider_name: str = "mistral", api_key: str = None) -> AIProvider:
    """
    Factory function to get AI provider instance.
    
    Args:
        provider_name: Name of the provider ('mistral' or 'nvidia')
        api_key: API key for the provider
        
    Returns:
        AIProvider instance
    """
    provider_class = PROVIDERS.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_name}. Available: {list(PROVIDERS.keys())}")
    
    return provider_class(api_key=api_key)


__all__ = ["AIProvider", "get_ai_provider", "MistralProvider", "NVIDIAProvider"]
