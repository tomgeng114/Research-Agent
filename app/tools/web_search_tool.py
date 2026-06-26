"""
WebSearchTool — simulates web search by calling the LLM with
a research-oriented prompt.

In production, this would be replaced with a real search API
(Tavily, SerpAPI, Brave Search, etc.).

Architecture note:
  The tool receives a search query and returns structured research
  notes. It uses the LLM's training knowledge as a proxy for search
  results, which works well for well-known topics.
"""
from __future__ import annotations

import logging
from typing import Any

from openai import OpenAI

from app.config import settings
from app.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    """
    LLM-powered research tool.

    Sends a research query to the LLM with a system prompt that
    instructs it to act as a comprehensive research assistant,
    returning structured, factual notes.
    """

    name: str = "web_search"
    description: str = (
        "Search the web for information on a specific topic. "
        "Provide a detailed search query and receive structured "
        "research notes with key findings, data points, and sources."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query or research question to investigate",
            },
            "focus_areas": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional specific aspects to focus on",
            },
        },
        "required": ["query"],
    }

    def __init__(self) -> None:
        import httpx

        transport = httpx.HTTPTransport(proxy=None, trust_env=False)
        self.client = OpenAI(
            api_key=settings.llm.api_key,
            base_url=settings.llm.base_url,
            http_client=httpx.Client(transport=transport),
        )

    def run(self, query: str, focus_areas: list[str] | None = None) -> dict[str, Any]:
        """
        Execute a research search.

        Args:
            query: The research question or search query
            focus_areas: Optional list of specific aspects to investigate

        Returns:
            Dict with 'query', 'findings', 'key_points', and 'raw_content'
        """
        focus_text = ""
        if focus_areas:
            focus_text = "\nFocus especially on these aspects:\n" + "\n".join(
                f"  - {f}" for f in focus_areas
            )

        system_prompt = (
            "You are an expert research assistant with deep knowledge across all domains. "
            "Your task is to provide comprehensive, factual, and well-structured research "
            "notes in response to a search query.\n\n"
            "Guidelines:\n"
            "1. Provide factual, detailed information\n"
            "2. Include data points, statistics, and examples where relevant\n"
            "3. Note key players, organizations, technologies, or concepts\n"
            "4. Highlight trends, debates, and different perspectives\n"
            "5. Structure your response with clear sections\n"
            "6. Note any limitations or uncertainties in the information\n"
            "7. Write in Chinese if the query is in Chinese, English if the query is in English"
        )

        messages = [
            {
                "role": "user",
                "content": f"Research the following topic thoroughly:\n\n{query}{focus_text}\n\n"
                "Provide structured research notes with:\n"
                "- Key findings\n"
                "- Important data points\n"
                "- Major perspectives or schools of thought\n"
                "- Recent developments\n"
                "- Relevant context",
            }
        ]

        try:
            response = self.client.chat.completions.create(
                model=settings.llm.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *messages,
                ],
                temperature=0.3,
                max_tokens=settings.llm.max_tokens,
            )
            content = response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("WebSearchTool failed for query '%s': %s", query, exc)
            return {
                "query": query,
                "error": str(exc),
                "findings": [],
                "raw_content": "",
            }

        # Extract key points (lines starting with - or numbered)
        key_points = [
            line.strip("- 0123456789. ")
            for line in content.split("\n")
            if line.strip() and (line.strip().startswith("-") or line.strip()[0].isdigit())
        ]

        return {
            "query": query,
            "findings": key_points[:15] if key_points else [],
            "raw_content": content,
        }
