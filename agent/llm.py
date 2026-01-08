import os
from openai import OpenAI
from typing import List, Dict, Any


class VeniceLLM:
    """Wrapper für Venice.ai (OpenAI-kompatibel)"""

    def __init__(self, model: str, temperature: float = 0.7, max_tokens: int = 4096):
        api_key = os.getenv("VENICE_API_KEY")
        if not api_key:
            raise ValueError("VENICE_API_KEY environment variable not set")

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.venice.ai/api/v1"
        )
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]] = None
    ) -> Any:
        """Chat Completion mit optionalen Tools"""

        params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        if tools:
            params["tools"] = tools

        return self.client.chat.completions.create(**params)
