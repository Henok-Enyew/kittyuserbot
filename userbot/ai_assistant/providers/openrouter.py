# OpenRouter AI Provider Implementation (OpenAI-compatible)
import aiohttp
from typing import Dict, List, Optional

from .base import AIProvider, openai_message_text


class OpenRouterProvider(AIProvider):
    """OpenRouter chat completions provider."""

    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    DEFAULT_MODEL = "openrouter/auto"

    def __init__(self, api_key: str = None, model: Optional[str] = None):
        super().__init__(api_key)
        self.model = model or self.DEFAULT_MODEL

    def get_provider_name(self) -> str:
        return "OpenRouter AI"

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # App attribution (optional for auth, recommended by OpenRouter)
            "HTTP-Referer": "https://github.com/Henok-Enyew/kittyuserbot",
            "X-Title": "kittyuserbot",
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
                        timeout=aiohttp.ClientTimeout(total=60),
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            if attempt < max_retries - 1:
                                continue
                            raise Exception(
                                f"OpenRouter API error ({response.status}): {error_text}"
                            )

                        data = await response.json()
                        content = openai_message_text(
                            (data.get("choices") or [{}])[0].get("message")
                        )
                        if not content:
                            if attempt < max_retries - 1:
                                continue
                            raise Exception("OpenRouter returned empty response")
                        return content

            except aiohttp.ClientError as e:
                if attempt < max_retries - 1:
                    continue
                raise Exception(f"Network error calling OpenRouter API: {str(e)}")
            except KeyError as e:
                if attempt < max_retries - 1:
                    continue
                raise Exception(
                    f"Unexpected OpenRouter API response format: {str(e)}"
                )
            except Exception as e:
                if attempt < max_retries - 1:
                    continue
                raise Exception(f"OpenRouter AI error: {str(e)}")

        raise Exception("OpenRouter AI failed after retries")
