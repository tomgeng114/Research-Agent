"""
Planner Agent — task decomposition and research planning.

Analyzes user's research topic and breaks it down into a
structured, sequential execution plan.

Output format:
  [
    {"step": 1, "title": "...", "query": "...", "focus_areas": [...]},
    {"step": 2, ...},
    ...
  ]
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base_agent import BaseAgent
from app.config import settings

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """
    Decomposes a research topic into an ordered sequence of steps.

    Each step includes a search query and optional focus areas
    that guide the ResearcherAgent's information gathering.
    """

    name: str = "planner"
    description: str = "Analyzes research topics and generates structured execution plans"

    @property
    def system_prompt(self) -> str:
        return (
            "You are a senior research planner. Your job is to decompose a research "
            "topic into a logical sequence of investigation steps.\n\n"
            "Rules:\n"
            "1. Produce 3-5 steps (no more, no less)\n"
            "2. Steps must be sequential and non-overlapping\n"
            "3. Each step must have a concrete search query\n"
            "4. Include focus areas to guide deep investigation\n"
            "5. The final step should always be synthesis/conclusion-oriented\n"
            "6. Respond in the same language as the user's topic\n"
            "7. Output ONLY valid JSON — no markdown, no explanation outside the JSON"
        )

    def run(
        self,
        topic: str,
        max_steps: int | None = None,
    ) -> dict[str, Any]:
        """
        Generate a research plan for the given topic.

        Args:
            topic: The research topic/question
            max_steps: Maximum number of research steps (default from settings)

        Returns:
            Dict with 'topic', 'plan' (list of steps), 'estimated_complexity'
        """
        max_steps = max_steps or settings.max_research_steps

        user_message = (
            f"Research topic: {topic}\n\n"
            f"Generate a research plan with 3-{max_steps} steps. "
            f"Output as JSON array with this structure:\n"
            f'[{{"step": 1, "title": "...", "query": "...", "focus_areas": [...]}}]\n\n'
            f"Make sure each query is specific and searchable. "
            f"The final step should synthesize findings into conclusions."
        )

        for attempt in range(3):
            try:
                raw = self.call_llm(
                    messages=[{"role": "user", "content": user_message}],
                    temperature=0.3,
                )
                plan = self._parse_plan(raw)
                if plan and len(plan) >= 2:
                    logger.info(
                        "[Planner] Generated %d-step plan for: %s", len(plan), topic
                    )
                    return {
                        "topic": topic,
                        "plan": plan,
                        "estimated_complexity": self._estimate_complexity(plan),
                    }
            except Exception as exc:
                logger.warning("[Planner] Attempt %d failed: %s", attempt + 1, exc)

        # Fallback: generate a simple plan
        fallback = self._fallback_plan(topic)
        logger.warning("[Planner] Using fallback plan for: %s", topic)
        return {
            "topic": topic,
            "plan": fallback,
            "estimated_complexity": "low",
        }

    # ── Parsing helpers ──────────────────────────────────────

    @staticmethod
    def _parse_plan(raw: str) -> list[dict[str, Any]] | None:
        """Extract JSON plan from LLM response."""
        # Try direct parse
        try:
            result = json.loads(raw.strip())
            if isinstance(result, list):
                return result
            if isinstance(result, dict) and "steps" in result:
                return result["steps"]
            if isinstance(result, dict) and "plan" in result:
                return result["plan"]
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        import re

        match = re.search(r"```(?:json)?\s*\n?(.*?)```", raw, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(1).strip())
                if isinstance(result, list):
                    return result
                if isinstance(result, dict):
                    return result.get("steps") or result.get("plan") or []
            except json.JSONDecodeError:
                pass

        return None

    @staticmethod
    def _fallback_plan(topic: str) -> list[dict[str, Any]]:
        """Generate a basic fallback plan when LLM parsing fails."""
        return [
            {
                "step": 1,
                "title": "背景与现状调研",
                "query": f"{topic} 的发展背景与当前现状",
                "focus_areas": ["历史背景", "当前状态", "关键指标"],
            },
            {
                "step": 2,
                "title": "核心技术分析",
                "query": f"{topic} 的核心技术与方法论",
                "focus_areas": ["技术架构", "关键方法", "创新点"],
            },
            {
                "step": 3,
                "title": "竞争格局与趋势",
                "query": f"{topic} 的竞争格局与发展趋势",
                "focus_areas": ["主要玩家", "市场动态", "未来方向"],
            },
            {
                "step": 4,
                "title": "综合结论",
                "query": f"{topic} 的综合分析与未来展望",
                "focus_areas": ["总结", "机会", "建议"],
            },
        ]

    @staticmethod
    def _estimate_complexity(plan: list[dict[str, Any]]) -> str:
        """Estimate research complexity based on plan structure."""
        n = len(plan)
        if n <= 3:
            return "low"
        if n <= 4:
            return "medium"
        return "high"
