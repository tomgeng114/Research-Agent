"""
Researcher Agent — executes research steps and gathers information.

Takes the Planner's output (list of research steps) and:
  1. Iterates through each step
  2. Calls WebSearchTool for each step's query
  3. Compiles structured research notes
  4. Augments findings with historical context from MemoryManager
"""
from __future__ import annotations

import logging
from typing import Any

from app.agents.base_agent import BaseAgent
from app.tools.web_search_tool import WebSearchTool

logger = logging.getLogger(__name__)


class ResearcherAgent(BaseAgent):
    """
    Executes research by processing each planned step through
    the web search tool and compiling structured notes.
    """

    name: str = "researcher"
    description: str = "Executes research steps and gathers structured information"

    def __init__(self) -> None:
        super().__init__()
        self.search_tool = WebSearchTool()
        self.register_tool(self.search_tool)

    @property
    def system_prompt(self) -> str:
        return (
            "You are a meticulous research analyst. Your job is to execute research "
            "steps and produce structured, factual notes. For each research query, "
            "you gather comprehensive information and organize it clearly.\n\n"
            "Guidelines:\n"
            "1. Be thorough — cover all focus areas\n"
            "2. Be factual — include data, dates, names, statistics\n"
            "3. Be structured — use clear sections and bullet points\n"
            "4. Note source quality and any information gaps\n"
            "5. Respond in the same language as the original research topic"
        )

    def run(
        self,
        topic: str,
        plan: list[dict[str, Any]],
        relevant_history: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute all research steps and return structured notes.

        Args:
            topic: The original research topic
            plan: List of research steps from PlannerAgent
            relevant_history: Optional historical research for context

        Returns:
            List of research notes, one dict per step
        """
        all_notes: list[dict[str, Any]] = []
        history_context = self._format_history(relevant_history)

        for step in plan:
            step_num = step.get("step", len(all_notes) + 1)
            title = step.get("title", f"Step {step_num}")
            query = step.get("query", topic)
            focus_areas = step.get("focus_areas", [])

            logger.info(
                "[Researcher] Step %d/%d: %s", step_num, len(plan), title
            )

            # Build enriched query with history context
            enriched_query = query
            if history_context:
                enriched_query = (
                    f"{query}\n\n[Historical context from previous research:\n"
                    f"{history_context}]"
                )

            # Execute web search
            search_result = self.search_tool.run(
                query=enriched_query,
                focus_areas=focus_areas,
            )

            # Compile step notes
            notes = {
                "step": step_num,
                "title": title,
                "query": query,
                "focus_areas": focus_areas,
                "findings": search_result.get("findings", []),
                "raw_content": search_result.get("raw_content", ""),
                "error": search_result.get("error"),
            }

            all_notes.append(notes)

        logger.info(
            "[Researcher] Completed %d steps for: %s", len(all_notes), topic
        )
        return all_notes

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _format_history(
        history: list[dict[str, Any]] | None,
    ) -> str:
        """Format historical research for inclusion in queries."""
        if not history:
            return ""

        parts = []
        for h in history:
            parts.append(
                f"- Previous research on '{h['topic']}' ({h['created_at']})"
            )
        return "\n".join(parts)

    def summarize_findings(
        self, notes: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Create a condensed summary of all research notes.

        Useful for passing concise context to the WriterAgent.
        """
        summary = []
        for note in notes:
            summary.append({
                "step": note["step"],
                "title": note["title"],
                "key_findings": note.get("findings", [])[:8],
                "has_error": bool(note.get("error")),
            })
        return summary
