from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseTool(ABC):
    """Basis-Klasse für alle Tools"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool-Name für LLM"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool-Beschreibung für LLM"""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON Schema für Tool-Parameter"""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Tool ausführen, gibt String zurück"""
        pass

    def to_openai_format(self) -> Dict[str, Any]:
        """Konvertiert zu OpenAI Function Calling Format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
