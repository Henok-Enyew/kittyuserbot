# Groq AI Provider Implementation (OpenAI-compatible)
import aiohttp
from typing import Dict, List, Optional

from .base import AIProvider, openai_message_text


class GroqProvider(AIProvider):
    """Groq Cloud chat completions provider."""

    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    DEFAULT_MODEL = "openai/gpt-oss-20b"

    def __init__(self, api_key: str = None, model: Optional[str] = None):
        super().__init__(api_key)
        self.model = model or self.DEFAULT_MODEL

    def get_provider_name(self) -> str:
        return "Groq AI"

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
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
        }

        max_retries = 2
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.API_URL,
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=45),
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            if attempt < max_retries - 1:
                                continue
                            raise Exception(
                                f"Groq API error ({response.status}): {error_text}"
                            )

                        data = await response.json()
                        content = openai_message_text(
                            (data.get("choices") or [{}])[0].get("message")
                        )
                        if not content:
                            if attempt < max_retries - 1:
                                continue
                            raise Exception("Groq returned empty response")
                        return content

            except aiohttp.ClientError as e:
                if attempt < max_retries - 1:
                    continue
                raise Exception(f"Network error calling Groq API: {str(e)}")
            except KeyError as e:
                if attempt < max_retries - 1:
                    continue
                raise Exception(f"Unexpected Groq API response format: {str(e)}")
            except Exception as e:
                if attempt < max_retries - 1:
                    continue
                raise Exception(f"Groq AI error: {str(e)}")

        raise Exception("Groq AI failed after retries")
