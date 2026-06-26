"""
ReportTool — saves research reports as Markdown files.

Generates well-formatted .md reports and stores them in the
configured reports directory.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class ReportTool(BaseTool):
    """
    Save a research report to disk as a Markdown file.

    Reports are saved to the configured reports_dir with a
    timestamped filename.
    """

    name: str = "save_report"
    description: str = (
        "Save a completed research report as a Markdown file. "
        "Use this after the research is complete to persist the final report."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "The research topic (used in filename and title)",
            },
            "content": {
                "type": "string",
                "description": "The full markdown content of the report",
            },
            "filename": {
                "type": "string",
                "description": "Optional custom filename (without .md extension)",
            },
        },
        "required": ["topic", "content"],
    }

    def run(
        self, topic: str, content: str, filename: str | None = None
    ) -> dict[str, Any]:
        """
        Save a markdown report to disk.

        Args:
            topic: Research topic
            content: Full markdown content
            filename: Optional custom filename

        Returns:
            Dict with 'filepath', 'topic', 'timestamp'
        """
        os.makedirs(settings.reports_dir, exist_ok=True)

        if filename:
            safe_name = filename.replace(" ", "_").replace("/", "_")
        else:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            safe_topic = topic[:60].replace(" ", "_").replace("/", "_")
            safe_name = f"{timestamp}_{safe_topic}"

        if not safe_name.endswith(".md"):
            safe_name += ".md"

        filepath = os.path.join(settings.reports_dir, safe_name)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info("Report saved: %s", filepath)

        return {
            "filepath": filepath,
            "filename": safe_name,
            "topic": topic,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "size_bytes": len(content.encode("utf-8")),
        }
