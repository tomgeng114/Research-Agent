"""
WebSearchTool — real web search via Tavily API, with LLM fallback.

Priority:
  1. Tavily API (if TAVILY_API_KEY is set) — real web search
  2. LLM fallback (if Tavily unavailable) — knowledge-based search

Return structure (unchanged):
  {
    "query": str,
    "findings": list[str],
    "raw_content": str
  }
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings
from app.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

# ── Tavily API ────────────────────────────────────────────────

TAVILY_URL = "https://api.tavily.com/search"


class _TavilyClient:
    """Minimal Tavily API client using httpx (no SDK dependency)."""

    def __init__(self, api_key: str) -> None:
        transport = httpx.HTTPTransport(proxy=None, trust_env=False)
        self._client = httpx.Client(transport=transport, timeout=30)
        self._api_key = api_key

    def search(
        self,
        query: str,
        search_depth: str = "basic",
        include_answer: bool = True,
        include_raw_content: bool = False,
        max_results: int = 10,
    ) -> dict[str, Any]:
        """Call Tavily Search API. Returns raw response dict."""
        payload: dict[str, Any] = {
            "api_key": self._api_key,
            "query": query,
            "search_depth": search_depth,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
            "max_results": max_results,
        }
        response = self._client.post(TAVILY_URL, json=payload)
        response.raise_for_status()
        return response.json()


def _tavily_response_to_findings(data: dict[str, Any]) -> tuple[list[str], str]:
    """
    Convert Tavily API response to our standard format.

    Tavily returns:
      - answer: str          — AI-generated answer summary
      - results: list[dict]  — each has title, url, content, score
      - images: list[dict]   — optional images

    Returns (findings, raw_content).
    """
    findings: list[str] = []
    raw_parts: list[str] = []

    # 1. AI answer (highest priority)
    answer = data.get("answer", "")
    if answer:
        findings.append(answer)
        raw_parts.append(f"## AI Summary\n\n{answer}")

    # 2. Search results
    results = data.get("results", [])
    if results:
        raw_parts.append(f"\n## Search Results ({len(results)} sources)\n")

    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        url = r.get("url", "")
        content = r.get("content", "")
        score = r.get("score", 0)

        # Build finding line
        if title:
            findings.append(f"[{title}]({url})")

        # Build raw content section
        raw_parts.append(f"\n### [{i}] {title}")
        raw_parts.append(f"URL: {url}")
        if score:
            raw_parts.append(f"Relevance: {score:.2f}")
        raw_parts.append(f"\n{content}")

    raw_content = "\n".join(raw_parts)

    # Deduplicate findings
    seen = set()
    unique_findings = []
    for f in findings:
        if f not in seen:
            seen.add(f)
            unique_findings.append(f)

    return unique_findings, raw_content


# ── WebSearchTool ─────────────────────────────────────────────


class WebSearchTool(BaseTool):
    """
    Hybrid web search tool.

    Uses Tavily API for real web search when TAVILY_API_KEY is configured.
    Falls back to LLM-based search when Tavily is unavailable.
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
        # Tavily client (optional)
        self._tavily: _TavilyClient | None = None
        if settings.tavily_api_key:
            self._tavily = _TavilyClient(settings.tavily_api_key)
            logger.info("WebSearchTool: Tavily API enabled")

        # LLM client (fallback)
        transport = httpx.HTTPTransport(proxy=None, trust_env=False)
        from openai import OpenAI

        self._llm = OpenAI(
            api_key=settings.llm.api_key,
            base_url=settings.llm.base_url,
            http_client=httpx.Client(transport=transport),
        )

    # ── Main entry ────────────────────────────────────────

    def run(self, query: str, focus_areas: list[str] | None = None) -> dict[str, Any]:
        """
        Execute research search.

        Args:
            query: The research question or search query
            focus_areas: Optional specific aspects to investigate

        Returns:
            Dict with 'query', 'findings', 'raw_content'
        """
        # ── Path A: Tavily real search ─────────────────
        if self._tavily:
            try:
                return self._run_tavily(query, focus_areas)
            except Exception as exc:
                logger.warning(
                    "Tavily search failed for '%s': %s — falling back to LLM",
                    query, exc,
                )

        # ── Path B: LLM fallback ───────────────────────
        return self._run_llm(query, focus_areas)

    # ── Tavily implementation ───────────────────────────

    def _run_tavily(
        self, query: str, focus_areas: list[str] | None
    ) -> dict[str, Any]:
        """
        Search via Tavily API.

        If focus_areas are provided, run a separate Tavily search
        for each area and merge results.
        """
        all_findings: list[str] = []
        all_raw: list[str] = []

        # Determine search queries
        queries = [query]
        if focus_areas:
            queries.extend(f"{query} {area}" for area in focus_areas)

        for q in queries:
            data = self._tavily.search(  # type: ignore[union-attr]
                query=q,
                search_depth="basic",
                include_answer=True,
            )
            findings, raw = _tavily_response_to_findings(data)
            all_findings.extend(findings)
            all_raw.append(raw)

        # Deduplicate findings
        seen = set()
        unique_findings = []
        for f in all_findings:
            if f not in seen:
                seen.add(f)
                unique_findings.append(f)

        logger.info(
            "Tavily: '%s' → %d findings, %d chars raw",
            query, len(unique_findings), sum(len(r) for r in all_raw),
        )

        return {
            "query": query,
            "findings": unique_findings,
            "raw_content": "\n\n".join(all_raw),
        }

    # ── LLM fallback ────────────────────────────────────

    def _run_llm(
        self, query: str, focus_areas: list[str] | None
    ) -> dict[str, Any]:
        """Fallback: LLM-based search (original behavior)."""
        logger.info("LLM fallback: '%s'", query)

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

        user_message = (
            f"Research the following topic thoroughly:\n\n{query}{focus_text}\n\n"
            "Provide structured research notes with:\n"
            "- Key findings\n"
            "- Important data points\n"
            "- Major perspectives or schools of thought\n"
            "- Recent developments\n"
            "- Relevant context"
        )

        try:
            response = self._llm.chat.completions.create(
                model=settings.llm.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.3,
                max_tokens=settings.llm.max_tokens,
            )
            content = response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("LLM fallback failed for '%s': %s", query, exc)
            return {
                "query": query,
                "error": str(exc),
                "findings": [],
                "raw_content": "",
            }

        # Extract key points
        key_points = [
            line.strip("- 0123456789. ")
            for line in content.split("\n")
            if line.strip()
            and (line.strip().startswith("-") or line.strip()[0].isdigit())
        ]

        return {
            "query": query,
            "findings": key_points[:15] if key_points else [],
            "raw_content": content,
        }
