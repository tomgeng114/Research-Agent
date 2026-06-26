"""
Research-Agent API — SSE streaming + REST endpoints.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.planner_agent import PlannerAgent
from app.agents.researcher_agent import ResearcherAgent
from app.agents.writer_agent import WriterAgent
from app.memory.memory_manager import MemoryManager
from app.tools.report_tool import ReportTool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# ── Lazy singletons ──────────────────────────────────────────

_planner: PlannerAgent | None = None
_researcher: ResearcherAgent | None = None
_writer: WriterAgent | None = None
_memory: MemoryManager | None = None
_report_tool: ReportTool | None = None


def _p():
    global _planner
    if not _planner:
        _planner = PlannerAgent()
    return _planner


def _r():
    global _researcher
    if not _researcher:
        _researcher = ResearcherAgent()
    return _researcher


def _w():
    global _writer
    if not _writer:
        _writer = WriterAgent()
    return _writer


def _m():
    global _memory
    if not _memory:
        _memory = MemoryManager()
    return _memory


def _rt():
    global _report_tool
    if not _report_tool:
        _report_tool = ReportTool()
    return _report_tool


# ── SSE helper ────────────────────────────────────────────────

def _sse(data: dict) -> str:
    """Format a dict as an SSE event."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# ── Models ────────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    topic: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="研究主题",
        examples=["分析 2026 年 AI Agent 的发展趋势"],
    )
    max_steps: int = Field(default=4, ge=2, le=6, description="研究步骤数")


# ── Streaming research ────────────────────────────────────────

@router.get("/research/stream")
async def research_stream(topic: str, max_steps: int = 4) -> StreamingResponse:
    """
    SSE 流式研究 — 实时推送每个阶段的进度和结果。
    前端用 EventSource 接收。
    """
    topic = topic.strip()
    if len(topic) < 3:
        raise HTTPException(400, "研究主题至少需要3个字符")

    async def event_stream() -> AsyncGenerator[str, None]:
        loop = asyncio.get_event_loop()

        # ── Phase 1: Plan ─────────────────────────────────
        yield _sse({"phase": "planning", "message": "正在分析研究主题，生成研究计划..."})

        try:
            plan_result = await loop.run_in_executor(
                None, lambda: _p().run(topic=topic, max_steps=max_steps)
            )
            plan = plan_result["plan"]
        except Exception as e:
            yield _sse({"phase": "error", "message": f"规划失败: {e}"})
            return

        yield _sse({
            "phase": "plan_done",
            "message": f"研究计划生成完毕，共 {len(plan)} 个步骤",
            "plan": [
                {"step": s["step"], "title": s["title"]}
                for s in plan
            ],
        })

        # ── Phase 2: Research ─────────────────────────────
        notes = []
        for i, step in enumerate(plan):
            step_num = step.get("step", i + 1)
            title = step.get("title", f"步骤 {step_num}")

            yield _sse({
                "phase": "researching",
                "message": f"正在执行第 {step_num}/{len(plan)} 步: {title}",
                "current_step": step_num,
                "total_steps": len(plan),
            })

            try:
                step_notes = await loop.run_in_executor(
                    None,
                    lambda s=step: _r().run(topic=topic, plan=[s]),
                )
                if step_notes:
                    notes.extend(step_notes)
                    yield _sse({
                        "phase": "step_done",
                        "message": f"第 {step_num} 步完成: {title}",
                        "step": {
                            "step": step_num,
                            "title": title,
                            "findings_count": len(step_notes[0].get("findings", [])),
                            "content_length": len(step_notes[0].get("raw_content", "")),
                            "sources_count": len(step_notes[0].get("sources", [])),
                        },
                    })
            except Exception as e:
                yield _sse({
                    "phase": "step_error",
                    "message": f"第 {step_num} 步出错: {e}",
                })
                notes.append({"step": step_num, "title": title, "findings": [], "error": str(e)})

        # ── Phase 3: Write ────────────────────────────────
        yield _sse({"phase": "writing", "message": "正在撰写研究报告..."})

        try:
            report = await loop.run_in_executor(
                None,
                lambda: _w().run(topic=topic, plan=plan, notes=notes),
            )
        except Exception as e:
            yield _sse({"phase": "error", "message": f"报告生成失败: {e}"})
            return

        # ── Phase 4: Save ─────────────────────────────────
        try:
            file_result = await loop.run_in_executor(
                None,
                lambda: _rt().run(topic=topic, content=report),
            )
            research_id = await loop.run_in_executor(
                None,
                lambda: _m().save_research(
                    topic=topic, plan=plan, notes=notes, report=report,
                ),
            )
        except Exception as e:
            yield _sse({"phase": "error", "message": f"保存失败: {e}"})
            return

        yield _sse({
            "phase": "done",
            "message": "研究完成！",
            "result": {
                "id": research_id,
                "topic": topic,
                "report": report,
                "report_path": file_result.get("filepath"),
                "plan": [{"step": s["step"], "title": s["title"]} for s in plan],
                "notes": [
                    {"step": n["step"], "title": n["title"], "findings": n.get("findings", [])[:5]}
                    for n in notes
                ],
            },
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── REST endpoints ────────────────────────────────────────────

class ResearchResponse(BaseModel):
    id: int | None = None
    topic: str = ""
    plan: list = []
    notes: list = []
    report: str = ""
    report_path: str | None = None


@router.post("/research", response_model=ResearchResponse)
def create_research(request: ResearchRequest) -> dict[str, Any]:
    """同步研究（阻塞模式，适合 API 调用）"""
    topic = request.topic.strip()
    plan_result = _p().run(topic=topic, max_steps=request.max_steps)
    plan = plan_result["plan"]
    notes = _r().run(topic=topic, plan=plan)
    report = _w().run(topic=topic, plan=plan, notes=notes)
    file_result = _rt().run(topic=topic, content=report)
    research_id = _m().save_research(topic=topic, plan=plan, notes=notes, report=report)
    return {
        "id": research_id, "topic": topic, "plan": plan,
        "notes": notes, "report": report,
        "report_path": file_result.get("filepath"),
    }


@router.get("/history")
def list_history(limit: int = 50, offset: int = 0) -> dict:
    """历史记录列表"""
    items = _m().list_research(limit=limit, offset=offset)
    return {"total": _m().get_count(), "items": items}


@router.get("/research/{research_id}")
def get_research(research_id: int) -> dict:
    """查看研究详情"""
    r = _m().get_research(research_id)
    if not r:
        raise HTTPException(404, "未找到该研究记录")
    return r


@router.delete("/research/{research_id}")
def delete_research(research_id: int) -> dict:
    """删除研究"""
    if not _m().delete_research(research_id):
        raise HTTPException(404, "未找到该研究记录")
    return {"status": "deleted", "id": research_id}
