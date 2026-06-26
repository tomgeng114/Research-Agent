"""
Writer Agent — synthesizes research findings into a polished report.

Takes the research notes from ResearcherAgent and:
  1. Organizes all findings
  2. Generates a structured Markdown report
  3. Produces conclusions and actionable recommendations
"""
from __future__ import annotations

import logging
from typing import Any

from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class WriterAgent(BaseAgent):
    """
    Synthesizes raw research notes into a polished, structured
    Markdown report with executive summary, detailed analysis,
    conclusions, and recommendations.
    """

    name: str = "writer"
    description: str = "Synthesizes research findings into structured reports"

    @property
    def system_prompt(self) -> str:
        return (
            "You are a senior research report writer. Your job is to synthesize "
            "raw research notes into polished, professional Markdown reports.\n\n"
            "Report structure requirements:\n"
            "1. Start with an Executive Summary (3-5 sentences)\n"
            "2. Organize findings into logical sections matching the research steps\n"
            "3. For each section, include a '参考来源' subsection listing the sources "
            "used in that section, formatted as: - [标题](URL)\n"
            "4. Include a dedicated Conclusions section\n"
            "5. End with actionable Recommendations\n"
            "6. At the very end, include a '## References' section "
            "that lists ALL sources as: - 标题：URL\n"
            "7. Use proper Markdown: headers, lists, bold, tables where appropriate\n"
            "8. Be objective — present multiple perspectives\n"
            "9. Include a 'Research Limitations' note\n"
            "10. Write the report in the same language as the topic\n"
            "11. Output ONLY the Markdown report — no preamble, no meta-commentary"
        )

    def run(
        self,
        topic: str,
        plan: list[dict[str, Any]],
        notes: list[dict[str, Any]],
    ) -> str:
        """
        Generate a complete research report.

        Args:
            topic: Original research topic
            plan: Research plan from PlannerAgent
            notes: Research notes from ResearcherAgent

        Returns:
            Complete Markdown report as a string
        """
        # Build the context for the writer
        context_parts = [f"# Research Topic\n{topic}\n"]

        # Add plan overview
        context_parts.append("\n## Research Plan\n")
        for step in plan:
            context_parts.append(
                f"- **Step {step.get('step')}**: {step.get('title')}"
            )

        # Add research findings
        context_parts.append("\n## Research Findings\n")
        all_sources: list[dict[str, str]] = []
        for note in notes:
            context_parts.append(f"\n### Step {note['step']}: {note['title']}")
            context_parts.append(f"**Search Query**: {note['query']}\n")

            if note.get("error"):
                context_parts.append(f"⚠️ Search error: {note['error']}\n")
                continue

            findings = note.get("findings", [])
            if findings:
                context_parts.append("**Key Findings:**\n")
                for f in findings[:10]:
                    context_parts.append(f"- {f}")
                context_parts.append("")

            # Include sources for this step
            step_sources = note.get("sources", [])
            if step_sources:
                context_parts.append("**Sources for this step:**\n")
                for s in step_sources:
                    context_parts.append(f"- [{s['title']}]({s['url']})")
                    all_sources.append(s)
                context_parts.append("")

            raw = note.get("raw_content", "")
            if raw:
                # Include full raw content but truncate if extremely long
                if len(raw) > 3000:
                    raw = raw[:3000] + "\n\n[... content truncated for conciseness ...]"
                context_parts.append(f"\n**Detailed Notes:**\n\n{raw}\n")

        context = "\n".join(context_parts)

        # Build References list for the end of the report
        refs_text = ""
        if all_sources:
            refs_text = "\n\n## All Sources (for References section)\n"
            for s in all_sources:
                refs_text += f"- {s['title']}：{s['url']}\n"

        user_message = (
            f"Using the research findings below, write a professional research report "
            f"on the topic: **{topic}**\n\n"
            f"The report must include:\n"
            f"1. Executive Summary\n"
            f"2. Sections corresponding to each research step — each section "
            f"must end with '参考来源' listing the sources used\n"
            f"3. Key Data & Statistics section (if applicable)\n"
            f"4. Conclusions\n"
            f"5. Recommendations\n"
            f"6. Research Limitations\n"
            f"7. A '## References' section at the very end listing ALL reference sources\n\n"
            f"Research data:\n\n{context}"
            f"{refs_text}"
        )

        for attempt in range(2):
            try:
                report = self.call_llm(
                    messages=[{"role": "user", "content": user_message}],
                    temperature=0.4,
                    max_tokens=4096,
                )
                if report and len(report) > 200:
                    logger.info(
                        "[Writer] Generated report: %d chars for: %s",
                        len(report),
                        topic,
                    )
                    return report.strip()
            except Exception as exc:
                logger.warning("[Writer] Attempt %d failed: %s", attempt + 1, exc)

        # Fallback
        return self._fallback_report(topic, plan, notes)

    # ── Fallback ──────────────────────────────────────────────

    @staticmethod
    def _fallback_report(
        topic: str,
        plan: list[dict[str, Any]],
        notes: list[dict[str, Any]],
    ) -> str:
        """Generate a basic report without LLM (if API fails)."""
        lines = [
            f"# {topic}",
            "",
            "## Executive Summary",
            "",
            f"This report investigates '{topic}' through {len(plan)} structured research steps.",
            "",
            "---",
            "",
        ]

        all_sources: list[dict[str, str]] = []
        for note in notes:
            step_label = note.get("title") or f"Step {note.get('step')}"
            lines.append(f"## {step_label}")
            lines.append("")
            findings = note.get("findings", [])
            if findings:
                for f in findings:
                    lines.append(f"- {f}")
            else:
                raw = note.get("raw_content", "")
                if raw:
                    lines.append(raw[:1000])
            # Add sources for this step
            step_sources = note.get("sources", [])
            if step_sources:
                lines.append("")
                lines.append("参考来源：")
                for s in step_sources:
                    lines.append(f"- [{s['title']}]({s['url']})")
                    all_sources.append(s)
            lines.append("")

        lines.extend([
            "---",
            "",
            "## Conclusions",
            "",
            "Based on the research findings above, key conclusions would be drawn here.",
            "",
            "## Recommendations",
            "",
            "1. Further investigation recommended",
            "2. Monitor developments in this area",
            "",
            "## Research Limitations",
            "",
            "- This report was generated with automated tool fallback (LLM unavailable)",
            f"- Research conducted at a single point in time",
            "",
        ])

        # References
        if all_sources:
            seen = set()
            lines.append("## References")
            lines.append("")
            for s in all_sources:
                if s["url"] not in seen:
                    seen.add(s["url"])
                    lines.append(f"- {s['title']}：{s['url']}")
            lines.append("")

        return "\n".join(lines)
