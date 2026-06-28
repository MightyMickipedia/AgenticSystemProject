"""Optimization endpoints with WebSocket live streaming."""

from __future__ import annotations

import asyncio
import time as _time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, WebSocket, WebSocketDisconnect

from calendar_optimizer.agents.flow import add_flow_handler, remove_flow_handler
from calendar_optimizer.agents.orchestrator import build_agent_squad
from calendar_optimizer.domain.calendar import WeeklyCalendar
from calendar_optimizer.report import render_markdown
from calendar_optimizer.web.dependencies import ensure_session, get_session

router = APIRouter()

_optimize_sessions: dict[str, dict[str, Any]] = {}


@router.post("/start")
async def start_optimization(
    request: Request,
    response: Response,
) -> dict[str, str]:
    session = ensure_session(request, response)
    calendar: WeeklyCalendar | None = session.get("calendar")
    if calendar is None:
        raise HTTPException(status_code=400, detail="No calendar loaded. Upload a calendar first.")

    optimize_id = uuid.uuid4().hex
    _optimize_sessions[optimize_id] = {
        "calendar": calendar,
        "session": session,
        "status": "pending",
    }
    return {"optimize_id": optimize_id}


@router.websocket("/ws/{optimize_id}")
async def optimization_websocket(websocket: WebSocket, optimize_id: str) -> None:
    if optimize_id not in _optimize_sessions:
        await websocket.close(code=4004, reason="Unknown optimization session")
        return

    await websocket.accept()
    opt = _optimize_sessions[optimize_id]
    calendar: WeeklyCalendar = opt["calendar"]
    session: dict[str, Any] = opt["session"]

    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    def flow_handler(message: str) -> None:
        queue.put_nowait({
            "type": "flow",
            "message": message,
            "timestamp": _time.time(),
        })

    async def sender() -> None:
        while True:
            msg = await queue.get()
            if msg is None:
                break
            try:
                await websocket.send_json(msg)
            except Exception:
                break

    async def run_optimization() -> None:
        add_flow_handler(flow_handler)
        try:
            squad, orchestrator = build_agent_squad(calendar)
            await squad.route_request(
                user_input="Optimize this calendar week in a balanced way.",
                user_id="web-user",
                session_id=f"week-{calendar.week_start.isoformat()}",
            )
            report = orchestrator.last_report
            if report is None:
                queue.put_nowait({
                    "type": "error",
                    "message": "Optimization produced no report. Check if Ollama is running.",
                })
            else:
                session["report"] = report
                queue.put_nowait({
                    "type": "calendar",
                    "data": calendar.model_dump(mode="json"),
                })
                queue.put_nowait({
                    "type": "report",
                    "data": report.model_dump(mode="json"),
                })
        except Exception as exc:
            queue.put_nowait({"type": "error", "message": str(exc)})
        finally:
            remove_flow_handler(flow_handler)
            queue.put_nowait(None)

    sender_task = asyncio.create_task(sender())
    optimize_task = asyncio.create_task(run_optimization())

    try:
        await optimize_task
        await sender_task
    except WebSocketDisconnect:
        optimize_task.cancel()
        sender_task.cancel()
    finally:
        _optimize_sessions.pop(optimize_id, None)


@router.get("/report/markdown")
async def download_report_markdown(request: Request) -> Response:
    session = get_session(request)
    calendar: WeeklyCalendar | None = session.get("calendar")
    report = session.get("report")
    if calendar is None or report is None:
        raise HTTPException(status_code=404, detail="No report available")

    md = render_markdown(calendar, report)
    return Response(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=week-{report.week_start.isoformat()}.md"},
    )
