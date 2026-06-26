"""
Central configuration for Research-Agent.

Supports DeepSeek (default) and OpenAI backends.
Loads from .env file in project root, then falls back to environment variables.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _load_dotenv() -> None:
    """Manually load .env file without python-dotenv dependency."""
    # Search for .env in project root (parent of app/)
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        os.path.join(os.getcwd(), ".env"),
        ".env",
    ]
    for path in candidates:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and value and key not in os.environ:
                        os.environ[key] = value
            break


# Load .env on import
_load_dotenv()


@dataclass
class LLMConfig:
    """LLM provider configuration. Uses OpenAI-compatible API format."""

    api_key: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", "sk-your-deepseek-key")
    )
    base_url: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )
    model: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    )
    temperature: float = 0.3
    max_tokens: int = 4096

    # Switch to OpenAI by setting env: LLM_PROVIDER=openai
    def __post_init__(self):
        provider = os.getenv("LLM_PROVIDER", "deepseek").lower()
        if provider == "openai":
            self.api_key = os.getenv("OPENAI_API_KEY", self.api_key)
            self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            self.model = os.getenv("OPENAI_MODEL", "gpt-4o")


@dataclass
class Settings:
    """Application settings."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    database_path: str = field(
        default_factory=lambda: os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "research_history.db",
        )
    )
    reports_dir: str = field(
        default_factory=lambda: os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "reports",
        )
    )
    max_research_steps: int = 5


settings = Settings()
