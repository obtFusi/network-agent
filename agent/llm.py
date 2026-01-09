import os
from openai import OpenAI
from typing import List, Dict, Any, Optional


class LLMClient:
    """Wrapper für OpenAI-kompatible APIs (Venice.ai, OpenAI, Ollama, etc.)"""

    # Default context limits für bekannte Models (Fallback)
    DEFAULT_CONTEXT_LIMITS = {
        "gpt-4": 8192,
        "gpt-4-turbo": 128000,
        "gpt-3.5-turbo": 16385,
        "llama-3.3-70b": 131072,
    }
    DEFAULT_CONTEXT_LIMIT = 4096

    def __init__(
        self,
        model: str,
        base_url: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        max_context_tokens: Optional[int] = None,
    ):
        # Config-Validierung
        if not model:
            raise ValueError(
                "model nicht konfiguriert!\n"
                "Bitte in config/settings.yaml unter llm.provider.model eintragen.\n"
                'Beispiel: model: "gpt-4" oder model: "llama-3.3-70b"'
            )
        if not base_url:
            raise ValueError(
                "base_url nicht konfiguriert!\n"
                "Bitte in config/settings.yaml unter llm.provider.base_url eintragen.\n"
                'Beispiel: base_url: "https://api.openai.com/v1"'
            )

        api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            raise ValueError(
                "LLM_API_KEY nicht gesetzt!\n"
                "Bitte in .env Datei eintragen: LLM_API_KEY=dein_key_hier"
            )

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._context_limit = max_context_tokens  # User override
        self._cached_context_limit = None

    def get_context_limit(self) -> int:
        """Ermittelt das Context-Limit für das aktuelle Model.

        Reihenfolge:
        1. User-Override aus Config (max_context_tokens)
        2. API /models Endpoint abfragen
        3. Bekannte Model-Defaults
        4. Konservativer Fallback (4096)
        """
        # User override hat Priorität
        if self._context_limit:
            return self._context_limit

        # Cache nutzen
        if self._cached_context_limit:
            return self._cached_context_limit

        # API abfragen
        try:
            models = self.client.models.list()
            for m in models.data:
                if m.id == self.model:
                    # Verschiedene Provider nutzen verschiedene Felder
                    limit = (
                        getattr(m, "context_length", None)
                        or getattr(m, "context_window", None)
                        or getattr(
                            getattr(m, "model_spec", None) or {},
                            "availableContextTokens",
                            None,
                        )
                    )
                    if limit:
                        self._cached_context_limit = limit
                        return limit
        except Exception:
            pass  # API nicht verfügbar, nutze Fallback

        # Bekannte Defaults
        limit = self.DEFAULT_CONTEXT_LIMITS.get(self.model, self.DEFAULT_CONTEXT_LIMIT)
        self._cached_context_limit = limit
        return limit

    def chat(
        self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]] = None
    ) -> Any:
        """Chat Completion mit optionalen Tools"""

        params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if tools:
            params["tools"] = tools

        return self.client.chat.completions.create(**params)
