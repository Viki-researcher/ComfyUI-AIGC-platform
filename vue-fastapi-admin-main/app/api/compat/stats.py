from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from tortoise.expressions import Q

from app.core.dependency import DependPermission
from app.models.admin import User
from app.models.platform import GenerationLog, Project
from app.schemas.base import Success

router = APIRouter(tags=["统计模块"])


def _parse_date(s: str, *, end_of_day: bool = False) -> datetime:
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt)
            if end_of_day and fmt == "%Y-%m-%d":
                dt = dt.replace(hour=23, minute=59, second=59)
            return dt
        except ValueError:
            pass
    raise ValueError("invalid date format")


@router.get("/stats", summary="统计聚合", dependencies=[DependPermission])
async def get_stats(
    dimension: str = Query("day", description="维度：day/project/user"),
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    project_id: int | None = Query(None, description="项目ID(可选)"),
    user_id: int | None = Query(None, description="用户ID(可选)"),
    status: str | None = Query(None, description="状态(可选，如 成功/失败)"),
):
    q = Q()
    if start_date:
        q &= Q(timestamp__gte=_parse_date(start_date))
    if end_date:
        q &= Q(timestamp__lte=_parse_date(end_date, end_of_day=True))
    if project_id is not None:
        q &= Q(project_id=project_id)
    if user_id is not None:
        q &= Q(user_id=user_id)
    if status:
        q &= Q(status=status)

    rows = await GenerationLog.filter(q).all()

    if dimension == "day":
        day_counts: dict[str, int] = defaultdict(int)
        for r in rows:
            day = r.timestamp.strftime("%Y-%m-%d")
            day_counts[day] += r.image_count
        data = [{"date": k, "count": day_counts[k]} for k in sorted(day_counts.keys())]
    elif dimension == "project":
        proj_counts: dict[int, int] = defaultdict(int)
        for r in rows:
            proj_counts[r.project_id] += r.image_count
        ids = list(proj_counts.keys())
        projects = {p.id: p for p in await Project.filter(id__in=ids).all()} if ids else {}
        data = [
            {
                "project_id": pid,
                "project_name": projects.get(pid).name if pid in projects else "",
                "count": proj_counts[pid],
            }
            for pid in sorted(proj_counts.keys())
        ]
    elif dimension == "user":
        user_counts: dict[int, int] = defaultdict(int)
        for r in rows:
            user_counts[r.user_id] += r.image_count
        ids = list(user_counts.keys())
        users = {u.id: u for u in await User.filter(id__in=ids).all()} if ids else {}
        data = [
            {
                "user_id": uid,
                "user_name": users.get(uid).username if uid in users else "",
                "count": user_counts[uid],
            }
            for uid in sorted(user_counts.keys())
        ]
    else:
        data = []

    return Success(data=data)


@router.get("/stats/trend", summary="时序趋势(按项目/用户)", dependencies=[DependPermission])
async def get_stats_trend(
    group_by: str = Query("project", description="分组维度：project/user"),
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
):
    q = Q()
    if start_date:
        q &= Q(timestamp__gte=_parse_date(start_date))
    if end_date:
        q &= Q(timestamp__lte=_parse_date(end_date, end_of_day=True))

    rows = await GenerationLog.filter(q).order_by("timestamp").all()

    dates_set: set[str] = set()
    series_map: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    if group_by == "project":
        for r in rows:
            day = r.timestamp.strftime("%Y-%m-%d")
            dates_set.add(day)
            series_map[str(r.project_id)][day] += r.image_count
        ids = [int(k) for k in series_map.keys()]
        projects = {p.id: p for p in await Project.filter(id__in=ids).all()} if ids else {}
        name_map = {str(pid): projects[pid].name if pid in projects else f"项目{pid}" for pid in ids}
    else:
        for r in rows:
            day = r.timestamp.strftime("%Y-%m-%d")
            dates_set.add(day)
            series_map[str(r.user_id)][day] += r.image_count
        ids = [int(k) for k in series_map.keys()]
        users = {u.id: u for u in await User.filter(id__in=ids).all()} if ids else {}
        name_map = {str(uid): users[uid].username if uid in users else f"用户{uid}" for uid in ids}

    dates = sorted(dates_set)
    series = []
    for key, day_counts in series_map.items():
        series.append({
            "name": name_map.get(key, key),
            "data": [day_counts.get(d, 0) for d in dates],
        })

    return Success(data={"dates": dates, "series": series})


@router.get("/export", summary="导出统计(Excel)", dependencies=[DependPermission])
async def export_stats(
    dimension: str = Query("day", description="维度：day/project/user"),
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    project_id: int | None = Query(None, description="项目ID(可选)"),
    user_id: int | None = Query(None, description="用户ID(可选)"),
    status: str | None = Query(None, description="状态(可选，如 成功/失败)"),
):
    q = Q()
    if start_date:
        q &= Q(timestamp__gte=_parse_date(start_date))
    if end_date:
        q &= Q(timestamp__lte=_parse_date(end_date, end_of_day=True))
    if project_id is not None:
        q &= Q(project_id=project_id)
    if user_id is not None:
        q &= Q(user_id=user_id)
    if status:
        q &= Q(status=status)
    rows = await GenerationLog.filter(q).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "stats"

    if dimension == "day":
        ws.append(["date", "count"])
        day_counts: dict[str, int] = defaultdict(int)
        for r in rows:
            day_counts[r.timestamp.strftime("%Y-%m-%d")] += r.image_count
        for k in sorted(day_counts.keys()):
            ws.append([k, day_counts[k]])
    elif dimension == "project":
        ws.append(["project_id", "project_name", "count"])
        proj_counts: dict[int, int] = defaultdict(int)
        for r in rows:
            proj_counts[r.project_id] += r.image_count
        ids = list(proj_counts.keys())
        projects = {p.id: p for p in await Project.filter(id__in=ids).all()} if ids else {}
        for pid in sorted(proj_counts.keys()):
            ws.append([pid, projects.get(pid).name if pid in projects else "", proj_counts[pid]])
    elif dimension == "user":
        ws.append(["user_id", "user_name", "count"])
        user_counts: dict[int, int] = defaultdict(int)
        for r in rows:
            user_counts[r.user_id] += r.image_count
        ids = list(user_counts.keys())
        users = {u.id: u for u in await User.filter(id__in=ids).all()} if ids else {}
        for uid in sorted(user_counts.keys()):
            ws.append([uid, users.get(uid).username if uid in users else "", user_counts[uid]])
    else:
        ws.append(["key", "count"])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    suffix = f"{(start_date or 'all').replace('-','')}_{(end_date or 'all').replace('-','')}"
    filename = f"stats_{dimension}_{suffix}.xlsx"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        buf,
        headers=headers,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
