"""
Unit tests for Research-Agent core components.

Tests cover:
  - Agent initialization
  - Tool base class
  - MemoryManager CRUD
  - Planner output parsing
  - API models

Run with:
    pytest tests/
    python -m pytest tests/
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Tool Tests ───────────────────────────────────────────────

def test_base_tool() -> None:
    """Test that BaseTool subclass works correctly."""
    from app.tools.base_tool import BaseTool

    class EchoTool(BaseTool):
        name = "echo"
        description = "Echoes input"
        parameters = {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        }

        def run(self, text: str = "") -> dict:
            return {"echo": text}

    tool = EchoTool()
    assert tool.name == "echo"
    assert tool.run(text="hello") == {"echo": "hello"}

    schema = tool.to_openai_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "echo"


def test_web_search_tool_init() -> None:
    """Test WebSearchTool can be instantiated."""
    from app.tools.web_search_tool import WebSearchTool

    tool = WebSearchTool()
    assert tool.name == "web_search"
    assert "query" in tool.parameters.get("required", [])


def test_report_tool() -> None:
    """Test ReportTool saves files correctly."""
    from app.tools.report_tool import ReportTool

    with tempfile.TemporaryDirectory() as tmpdir:
        # Override reports dir
        import app.config
        original = app.config.settings.reports_dir
        app.config.settings.reports_dir = tmpdir

        try:
            tool = ReportTool()
            result = tool.run(
                topic="Test Topic",
                content="# Test Report\n\nHello World",
            )
            assert os.path.exists(result["filepath"])
            assert result["topic"] == "Test Topic"

            with open(result["filepath"], "r", encoding="utf-8") as f:
                content = f.read()
            assert "# Test Report" in content
            assert "Hello World" in content
        finally:
            app.config.settings.reports_dir = original


# ── Memory Tests ─────────────────────────────────────────────

def test_memory_manager_crud() -> None:
    """Test full CRUD cycle for MemoryManager."""
    from app.memory.memory_manager import MemoryManager

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        mm = MemoryManager(db_path)

        # Create
        rid = mm.save_research(
            topic="Test research",
            plan=[{"step": 1, "title": "Step 1"}],
            notes=[{"step": 1, "findings": ["finding A"]}],
            report="# Test Report",
        )
        assert rid > 0

        # Read
        result = mm.get_research(rid)
        assert result is not None
        assert result["topic"] == "Test research"
        assert result["plan"] == [{"step": 1, "title": "Step 1"}]

        # List
        items = mm.list_research()
        assert len(items) >= 1
        assert items[0]["topic"] == "Test research"

        # Search
        results = mm.search_by_topic("Test")
        assert len(results) >= 1

        # Count
        assert mm.get_count() >= 1

        # Delete
        assert mm.delete_research(rid) is True
        assert mm.get_research(rid) is None
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_memory_relevant_history() -> None:
    """Test relevant history retrieval."""
    from app.memory.memory_manager import MemoryManager

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        mm = MemoryManager(db_path)
        mm.save_research(topic="AI Agent Development", report="...")
        mm.save_research(topic="Machine Learning Basics", report="...")
        mm.save_research(topic="AI Safety Research", report="...")

        results = mm.get_relevant_history("AI Agent", limit=2)
        assert len(results) >= 1
        # Should match "AI Agent Development" first
        assert "AI Agent" in results[0]["topic"] or "AI" in results[0]["topic"]
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


# ── Agent Tests ──────────────────────────────────────────────

def test_planner_agent_init() -> None:
    """Test PlannerAgent can be instantiated."""
    from app.agents.planner_agent import PlannerAgent

    agent = PlannerAgent()
    assert agent.name == "planner"
    assert len(agent.system_prompt) > 0


def test_planner_parse_plan() -> None:
    """Test plan parsing from LLM output."""
    from app.agents.planner_agent import PlannerAgent

    agent = PlannerAgent()

    # Test valid JSON array
    raw = json.dumps([
        {"step": 1, "title": "Background", "query": "test query"},
        {"step": 2, "title": "Analysis", "query": "analysis query"},
    ])
    plan = agent._parse_plan(raw)
    assert plan is not None
    assert len(plan) == 2

    # Test markdown code block
    raw_md = "```json\n" + json.dumps([
        {"step": 1, "title": "Test", "query": "q"},
    ]) + "\n```"
    plan2 = agent._parse_plan(raw_md)
    assert plan2 is not None
    assert len(plan2) == 1

    # Test invalid
    assert agent._parse_plan("not json at all") is None


def test_planner_fallback_plan() -> None:
    """Test fallback plan generation."""
    from app.agents.planner_agent import PlannerAgent

    plan = PlannerAgent._fallback_plan("AI Testing")
    assert len(plan) >= 3
    assert all("step" in s for s in plan)
    assert all("query" in s for s in plan)


def test_researcher_agent_init() -> None:
    """Test ResearcherAgent initialization."""
    from app.agents.researcher_agent import ResearcherAgent

    agent = ResearcherAgent()
    assert agent.name == "researcher"
    assert "web_search" in agent._tools


def test_writer_agent_init() -> None:
    """Test WriterAgent initialization."""
    from app.agents.writer_agent import WriterAgent

    agent = WriterAgent()
    assert agent.name == "writer"


def test_writer_fallback_report() -> None:
    """Test fallback report generation."""
    from app.agents.writer_agent import WriterAgent

    plan = [{"step": 1, "title": "Background"}]
    notes = [{"step": 1, "title": "Background", "findings": ["Key point 1"]}]
    report = WriterAgent._fallback_report("Test", plan, notes)
    assert "# Test" in report
    assert "Key point 1" in report


# ── Config Tests ─────────────────────────────────────────────

def test_settings_defaults() -> None:
    """Test default settings."""
    from app.config import Settings

    s = Settings()
    assert s.llm.model == "deepseek-chat"
    assert s.max_research_steps == 5


# ── API Model Tests ──────────────────────────────────────────

def test_research_request_model() -> None:
    """Test Pydantic model validation."""
    from app.api.routes import ResearchRequest

    req = ResearchRequest(topic="Test topic")
    assert req.topic == "Test topic"
    assert req.max_steps == 5

    # Test min length
    try:
        ResearchRequest(topic="ab")  # too short
        assert False, "Should have raised validation error"
    except Exception:
        pass
