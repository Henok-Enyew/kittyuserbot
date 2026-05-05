# Base AI Provider Interface
from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class AIProvider(ABC):
    """
    Abstract base class for AI providers.
    All AI providers must implement this interface.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self._validate_api_key()
    
    def _validate_api_key(self):
        """Validate that API key is provided"""
        if not self.api_key:
            raise ValueError(f"{self.__class__.__name__} requires an API key")
    
    @abstractmethod
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """
        Generate AI response from conversation messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
                     Example: [{"role": "user", "content": "Hello"}]
            temperature: Creativity level (0.0 to 1.0)
            max_tokens: Maximum response length
            
        Returns:
            Generated text response
            
        Raises:
            Exception: If API call fails
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of this provider"""
        pass
