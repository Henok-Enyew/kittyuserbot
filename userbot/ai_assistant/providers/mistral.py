# Mistral AI Provider Implementation
import aiohttp
from typing import List, Dict
from .base import AIProvider


class MistralProvider(AIProvider):
    """Mistral AI provider implementation"""
    
    API_URL = "https://api.mistral.ai/v1/chat/completions"
    DEFAULT_MODEL = "mistral-small-latest"
    
    def get_provider_name(self) -> str:
        return "Mistral AI"
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """
        Generate response using Mistral AI API.
        
        Args:
            messages: Conversation history
            temperature: Response creativity
            max_tokens: Max response length
            
        Returns:
            Generated response text
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.DEFAULT_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Retry logic
        max_retries = 2
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.API_URL,
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            if attempt < max_retries - 1:
                                continue  # Retry
                            raise Exception(f"Mistral API error ({response.status}): {error_text}")
                        
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"].strip()
                        
                        # Handle empty responses
                        if not content:
                            if attempt < max_retries - 1:
                                continue  # Retry
                            raise Exception("Mistral returned empty response")
                        
                        return content
            
            except aiohttp.ClientError as e:
                if attempt < max_retries - 1:
                    continue  # Retry
                raise Exception(f"Network error calling Mistral API: {str(e)}")
            except KeyError as e:
                if attempt < max_retries - 1:
                    continue  # Retry
                raise Exception(f"Unexpected Mistral API response format: {str(e)}")
            except Exception as e:
                if attempt < max_retries - 1:
                    continue  # Retry
                raise Exception(f"Mistral AI error: {str(e)}")
        
        raise Exception("Mistral AI failed after retries")
