# NVIDIA AI Provider Implementation
import aiohttp
from typing import Dict, List, Optional

from .base import AIProvider, openai_message_text


class NVIDIAProvider(AIProvider):
    """NVIDIA AI provider implementation (OpenAI-compatible NIM endpoint)."""

    API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
    DEFAULT_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"

    def __init__(self, api_key: str = None, model: Optional[str] = None):
        """
        Initialize NVIDIA provider.

        Args:
            api_key: NVIDIA API key
            model: Optional model override (defaults to DEFAULT_MODEL)
        """
        super().__init__(api_key)
        self.model = model or self.DEFAULT_MODEL

    def get_provider_name(self) -> str:
        return "NVIDIA AI"

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        """Generate response using NVIDIA AI API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            # Nemotron thinking mode fills reasoning_content and can empty content
            "chat_template_kwargs": {"enable_thinking": False},
        }

        max_retries = 2
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.API_URL,
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=60),
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            if attempt < max_retries - 1:
                                continue
                            raise Exception(
                                f"NVIDIA API error ({response.status}): {error_text}"
                            )

                        data = await response.json()
                        content = openai_message_text(
                            (data.get("choices") or [{}])[0].get("message")
                        )

                        if not content:
                            if attempt < max_retries - 1:
                                continue
                            raise Exception("NVIDIA returned empty response")

                        return content

            except aiohttp.ClientError as e:
                if attempt < max_retries - 1:
                    continue
                raise Exception(f"Network error calling NVIDIA API: {str(e)}")
            except KeyError as e:
                if attempt < max_retries - 1:
                    continue
                raise Exception(f"Unexpected NVIDIA API response format: {str(e)}")
            except Exception as e:
                if attempt < max_retries - 1:
                    continue
                raise Exception(f"NVIDIA AI error: {str(e)}")

        raise Exception("NVIDIA AI failed after retries")
