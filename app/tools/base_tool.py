"""
Base tool class — all tools inherit from this.

Follows standard Tool Calling architecture:
  - name: unique tool identifier
  - description: what the tool does (for LLM tool selection)
  - parameters: JSON Schema describing input arguments
  - run(): execute the tool
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """
    Abstract base for all tools.

    Subclasses must define:
      - name: str       — unique identifier
      - description: str — human + LLM-readable description
      - parameters: dict — JSON Schema for function parameters
      - run(**kwargs)    — execute the tool
    """

    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """Execute the tool with the given arguments."""
        ...

    def to_openai_schema(self) -> dict[str, Any]:
        """Return OpenAI function-calling compatible schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.name}'>"
