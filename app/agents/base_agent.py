"""
Base agent class — all agents inherit from this.

Provides:
  - LLM calling via OpenAI-compatible API
  - Tool registration and invocation
  - Structured output parsing helpers
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base for all agents.

    Subclasses must define:
      - name: str
      - description: str
      - system_prompt: str
    """

    name: str = "base"
    description: str = "Base agent"

    def __init__(self) -> None:
        import httpx

        transport = httpx.HTTPTransport(proxy=None, trust_env=False)
        self.client = OpenAI(
            api_key=settings.llm.api_key,
            base_url=settings.llm.base_url,
            http_client=httpx.Client(transport=transport),
        )
        self.model = settings.llm.model
        self._tools: dict[str, Any] = {}

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt that defines agent behavior."""
        ...

    # ── LLM calling ──────────────────────────────────────────

    def call_llm(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """
        Call the LLM with the given message history.

        Args:
            messages: Chat-style message list [{"role":..., "content":...}]
            temperature: Override default temperature
            max_tokens: Override default max_tokens

        Returns:
            LLM response text
        """
        temp = temperature if temperature is not None else settings.llm.temperature
        max_tok = max_tokens if max_tokens is not None else settings.llm.max_tokens

        full_messages = [{"role": "system", "content": self.system_prompt}] + messages

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=temp,
                max_tokens=max_tok,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("[%s] LLM call failed: %s", self.name, exc)
            raise

    def call_llm_with_tools(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """
        Call the LLM with tool definitions (function calling).

        Returns parsed tool call args or None if no tool was called.
        """
        temp = temperature if temperature is not None else settings.llm.temperature

        full_messages = [{"role": "system", "content": self.system_prompt}] + messages

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=temp,
                tools=tools,
                tool_choice="auto",
            )
        except Exception as exc:
            logger.error("[%s] Tool-calling LLM failed: %s", self.name, exc)
            raise

        choice = response.choices[0]
        if choice.message.tool_calls:
            tc = choice.message.tool_calls[0]
            try:
                return {
                    "tool_name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                }
            except json.JSONDecodeError:
                return {
                    "tool_name": tc.function.name,
                    "arguments": {"raw": tc.function.arguments},
                }
        return {}

    # ── Tool management ──────────────────────────────────────

    def register_tool(self, tool: Any) -> None:
        """Register a tool instance for this agent."""
        self._tools[tool.name] = tool

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return OpenAI-format tool definitions for all registered tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Execute a registered tool by name."""
        tool = self._tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not registered for agent '{self.name}'")
        logger.info("[%s] executing tool: %s(%s)", self.name, tool_name, arguments)
        return tool.run(**arguments)

    # ── Abstract run method ──────────────────────────────────

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """Execute the agent's primary task."""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.name}'>"
