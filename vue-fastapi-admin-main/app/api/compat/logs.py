from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from tortoise.expressions import Q

from app.core.ctx import CTX_USER_ID
from app.core.dependency import DependPermission
from app.models.admin import User
from app.models.platform import GenerationLog, Project
from app.schemas.base import Success
from app.schemas.platform import GenerationLogCreate

router = APIRouter(prefix="/logs", tags=["日志模块"])


def _now_str(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


@router.post("", summary="写入生成日志", dependencies=[DependPermission])
async def create_log(req_in: GenerationLogCreate):
    user_id = CTX_USER_ID.get()
    ts = req_in.timestamp or datetime.now()

    obj = await GenerationLog.create(
        user_id=user_id,
        project_id=req_in.project_id,
        timestamp=ts,
        status=req_in.status,
        prompt_id=req_in.prompt_id,
        concurrent_id=req_in.concurrent_id,
        details=req_in.details,
    )

    return Success(
        data={
            "id": obj.id,
            "user_id": obj.user_id,
            "project_id": obj.project_id,
            "timestamp": _now_str(obj.timestamp),
            "status": obj.status,
            "prompt_id": obj.prompt_id,
            "concurrent_id": obj.concurrent_id,
            "details": obj.details,
        }
    )


def _parse_dt(s: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise ValueError("invalid datetime format")


def _build_log_query(
    user_id: int | None,
    project_id: int | None,
    status: str | None,
    start: str | None,
    end: str | None,
) -> Q:
    q = Q()
    if user_id is not None:
        q &= Q(user_id=user_id)
    if project_id is not None:
        q &= Q(project_id=project_id)
    if status:
        q &= Q(status=status)
    if start:
        q &= Q(timestamp__gte=_parse_dt(start))
    if end:
        q &= Q(timestamp__lte=_parse_dt(end))
    return q


@router.get("", summary="查询生成日志", dependencies=[DependPermission])
async def list_logs(
    user_id: int | None = Query(None, description="用户ID(可选)"),
    project_id: int | None = Query(None, description="项目ID(可选)"),
    status: str | None = Query(None, description="状态(可选，如 成功/失败)"),
    start: str | None = Query(None, description="开始时间 YYYY-MM-DD 或 YYYY-MM-DD HH:mm:ss"),
    end: str | None = Query(None, description="结束时间 YYYY-MM-DD 或 YYYY-MM-DD HH:mm:ss"),
    current: int = Query(1, ge=1, description="当前页"),
    size: int = Query(20, ge=1, le=200, description="每页数量"),
):
    q = _build_log_query(user_id, project_id, status, start, end)

    total = await GenerationLog.filter(q).count()
    rows = (
        await GenerationLog.filter(q)
        .order_by("-timestamp")
        .offset((current - 1) * size)
        .limit(size)
        .all()
    )

    # 轻量补齐 user/project 名称
    user_ids = sorted({r.user_id for r in rows})
    project_ids = sorted({r.project_id for r in rows})
    users = {u.id: u for u in await User.filter(id__in=user_ids).all()} if user_ids else {}
    projects = {p.id: p for p in await Project.filter(id__in=project_ids).all()} if project_ids else {}

    records = []
    for r in rows:
        records.append(
            {
                "id": r.id,
                "timestamp": _now_str(r.timestamp),
                "user": users.get(r.user_id).username if r.user_id in users else "",
                "project": projects.get(r.project_id).name if r.project_id in projects else "",
                "status": r.status,
                "details": r.details,
                "concurrent_id": r.concurrent_id,
            }
        )

    return Success(
        data={
            "records": records,
            "current": current,
            "size": size,
            "total": total,
        }
    )


@router.get("/export", summary="导出生成日志(Excel)", dependencies=[DependPermission])
async def export_logs(
    user_id: int | None = Query(None, description="用户ID(可选)"),
    project_id: int | None = Query(None, description="项目ID(可选)"),
    status: str | None = Query(None, description="状态(可选)"),
    start: str | None = Query(None, description="开始时间"),
    end: str | None = Query(None, description="结束时间"),
):
    q = _build_log_query(user_id, project_id, status, start, end)
    rows = await GenerationLog.filter(q).order_by("-timestamp").all()

    user_ids = sorted({r.user_id for r in rows})
    project_ids = sorted({r.project_id for r in rows})
    users = {u.id: u for u in await User.filter(id__in=user_ids).all()} if user_ids else {}
    projects = {p.id: p for p in await Project.filter(id__in=project_ids).all()} if project_ids else {}

    wb = Workbook()
    ws = wb.active
    ws.title = "generation_logs"
    ws.append(["ID", "时间", "用户", "项目", "状态", "并发ID", "详情"])

    for r in rows:
        ws.append([
            r.id,
            _now_str(r.timestamp),
            users.get(r.user_id).username if r.user_id in users else str(r.user_id),
            projects.get(r.project_id).name if r.project_id in projects else str(r.project_id),
            r.status,
            r.concurrent_id or "",
            str(r.details) if r.details else "",
        ])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"generation_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        buf,
        headers=headers,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

